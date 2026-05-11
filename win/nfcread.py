# nfcread.py
# Uses nfcpy to drive an NFC tag reader to continuously scan for
# supported tags. Commands can be executed based on tag IDs.

# This file is in the public domain (Unlicense). https://unlicense.org

import random
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

import nfc
import tomllib
from pynput import keyboard
from serial import SerialException


@dataclass
class LaunchInfo:
    """Dataclass for global state regarding the most recently executed command."""

    button_active: bool = False
    "Button command is active. If true, an NFC scan can cancel the command."

    button_listening: bool = True
    "Currently listening for the button press. Set to false when an NFC tag is scanned, and momentarily false when the button is pressed as a debouncing measure."

    button_pressed: bool = False
    "The most recent command was launched with the button."

    button_last_press_time = time.time()
    "Timestamp for the last time a button press was accepted."

    launch_method: Optional[int] = None
    "Set to the value in the enum `methods` for the method of the current command, or `None` when no command is running."

    lock: threading.Lock = threading.Lock()
    "A `threading.Lock` object, to safely access the button variables."

    def stop_button_listening(self):
        with self.lock:
            self.button_listening = False
            self.button_active = False

    def start_button_listening(self):
        with self.lock:
            self.button_listening = True


class NFCConfig:
    """Class for NFC reader configuration."""

    def __init__(self):
        self.clf = nfc.ContactlessFrontend()
        self.connected = False
        self.com_port = "0"
        self.driver = ""
        self.remove_timeout = 0


def connect_nfc_reader(nfc_config: NFCConfig):
    serial_error_message = False
    com_port = int(nfc_config.com_port)
    if com_port > 0:
        while True:
            try:
                nfc_config.clf.open(f"com:{nfc_config.com_port}:{nfc_config.driver}")
                print(
                    f"{nfc_config.driver} NFC reader on COM{nfc_config.com_port} opened."
                )
                nfc_config.connected = True
                return
            except SerialException:
                if not serial_error_message:
                    print(
                        f"No {nfc_config.driver} NFC reader detected on COM{nfc_config.com_port}. Waiting until it becomes available."
                    )
                    serial_error_message = True
                time.sleep(1)
    else:
        print("Autodetecting NFC reader.")
        while True:
            result = nfc_config.clf.open("com")
            if result and nfc_config.clf.device is not None:
                print(
                    f"{nfc_config.driver} NFC reader on {nfc_config.clf.device.path} opened."
                )
                nfc_config.connected = True
                return
            else:
                time.sleep(1)


def start_button_listener(li: LaunchInfo, button_code):
    """Returns a `pynput` thread that listens for the keyboard shortcut."""

    def on_press(key):
        if not li.button_listening:
            print("Button press ignored.")
            return
        if key != button_code:
            return
        with li.lock:
            li.button_pressed = True

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    return listener


def main():

    launch_info: LaunchInfo = LaunchInfo()

    try:
        with open("nfcread.toml", "rb") as nfc_toml_file:
            nfc_toml = tomllib.load(nfc_toml_file)
    except IOError:
        print("nfcread.toml not found.")
        exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"Error reading nfcread.toml: {e}")
        exit(1)

    nfc_config = NFCConfig()

    nfc_config.com_port = str(nfc_toml["reader"]["com_port"])
    nfc_config.driver = nfc_toml["reader"]["driver"]
    nfc_config.remove_timeout = nfc_toml["reader"]["remove_timeout"]

    tag_commands = nfc_toml["tag_commands"]

    remove_timeout = 0
    current_tag = None
    command = None
    old_command = None
    log_new_tags = nfc_toml["reader"]["log_new_tags"]
    new_tags_file_write_error = False
    new_tags = set()

    # Get button commands list based on whitelist/blacklist settings.
    button_commands = []
    button_commands_src = []
    try:
        button_code = keyboard.Key[nfc_toml["button"]["key"].lower()]
    except KeyError:
        button_code = keyboard.KeyCode.from_char(nfc_toml["button"]["key"])
    
    if nfc_toml["button"]["button_enabled"]:
        start_button_listener(launch_info,button_code)
        if nfc_toml["button"]["whitelist"]:
            button_commands_src: list[str] = nfc_toml["button"]["whitelist_commands"]
        else:
            button_commands_src = nfc_toml["tag_commands"].values()
            if nfc_toml["button"]["blacklist"]:
                button_commands_blacklist = nfc_toml["button"]["blacklist_commands"]
                button_commands_src = [i for i in button_commands_src if i not in button_commands_blacklist]
        button_commands: list[str] = button_commands_src.copy()
        random.shuffle(button_commands)
                      
    while True:
        # Button loop.
        if nfc_toml["button"]["button_enabled"]:
            if launch_info.button_pressed:
                print("Button pressed.")
                with launch_info.lock:
                    launch_info.button_pressed = False

                button_press_time = time.time()

                # If the button is pressed, launch a random command if no command is running,
                # or exit the current command if it is running.
                if not launch_info.button_active and (
                    button_press_time - launch_info.button_last_press_time > 2
                ):
                    # Get a command from the button_commands list. 
                    # If it's empty, copy the source list and shuffle.
                    if len(button_commands) == 0:
                        button_commands = button_commands_src.copy()
                        random.shuffle(button_commands)

                    new_button_command = button_commands.pop()
                    subprocess.Popen(new_button_command, shell=True)
                    launch_info.button_active = True
                    launch_info.button_last_press_time = button_press_time
                elif launch_info.button_active and (
                    button_press_time - launch_info.button_last_press_time > 5
                ):
                    exit_action = subprocess.Popen("exit.bat", shell=True)
                    while True:
                        try:
                            exit_action.wait(timeout=3)
                            break
                        except TimeoutError:
                            print("Exit action timed out. Retrying.")
                            continue

                    launch_info.button_active = False
                    launch_info.button_last_press_time = button_press_time

        # NFC loop.
        try:

            # Open the NFC device for the first time, or if it was
            # disconnected due to an error.
            if not nfc_config.connected:
                connect_nfc_reader(nfc_config)

            target = nfc_config.clf.sense(nfc.clf.RemoteTarget("106A"), iterations=1)
            if target:
                if hasattr(target, "sdd_res"):
                    print(f"Tag scanned. ID: {target.sdd_res.hex()}")
                    tag_id = target.sdd_res.hex()

                    # If a tag was removed and a different tag is read
                    # before the remove timeout, execute the exit action
                    # immediately before executing the new command.
                    # Wait 1 second after the exit action completes before
                    # continuing to ensure cleanup has completed.
                    if current_tag is not None and current_tag != tag_id:
                        print("Executing exit action before new command.")
                        exit_action = subprocess.Popen("exit.bat", shell=True)
                        while True:
                            try:
                                exit_action.wait(timeout=3)
                                break
                            except TimeoutError:
                                print("Exit action timed out. Retrying.")
                                continue
                        time.sleep(1)
                    launch_info.stop_button_listening()
                    current_tag = tag_id
                    command = tag_commands.get(tag_id)
                    if command is not None and old_command != command:
                        remove_timeout = nfc_config.remove_timeout
                        print(f"Executing command: {command}")
                        old_command = command
                        subprocess.Popen(command, shell=True)
                    elif old_command == command and old_command is not None:
                        print("Prior tag scanned. Cancelling exit action.")
                        remove_timeout = nfc_config.remove_timeout
                    else:
                        if log_new_tags and tag_id not in new_tags:
                            new_tags.add(tag_id)
                            try:
                                with open("new_tags.txt", "a") as file:
                                    file.write(tag_id + "\n")
                            except IOError:
                                new_tags_file_write_error = True
                                print(
                                    "Error writing to new_tags.txt. New tag ID(s) will be written to console when the program exits."
                                )
                        print("No command defined for this tag.")
                        remove_timeout = 0
                else:
                    print("Unsupported tag scanned.")

                # Idle while tag is present.
                while nfc_config.clf.sense(nfc.clf.RemoteTarget("106A"), iterations=1):
                    pass
            else:
                if current_tag is not None:
                    if command is not None:
                        if remove_timeout == nfc_config.remove_timeout:
                            print(
                                f"Tag removed. Waiting {nfc_config.remove_timeout} seconds before executing exit action."
                            )
                        if remove_timeout > 0:
                            print(f"Remaining time: {remove_timeout}")
                            remove_timeout -= 1
                            time.sleep(1)
                        else:
                            exit_action = subprocess.Popen("exit.bat", shell=True)
                            while True:
                                try:
                                    exit_action.wait(timeout=3)
                                    break
                                except TimeoutError:
                                    print("Exit action timed out. Retrying.")
                                    continue
                            current_tag = None
                            command = None
                            old_command = None
                            launch_info.start_button_listening()
                    else:
                        print("Tag removed.")
                        current_tag = None
                        command = None
                        old_command = None

        except OSError as e:
            print(f"Error: {e}")
            print("Reconnecting NFC reader.")
            nfc_config.connected = False
            continue
        except KeyboardInterrupt:
            break

    if len(new_tags) > 0:
        if not new_tags_file_write_error:
            print(f"{len(new_tags)} tag ID(s) written to new_tags.txt.\n")
        else:
            print(
                f"Error writing to new_tags.txt. {len(new_tags)} new tag ID(s) listed below:"
            )
            for i in new_tags:
                print(i)

    print("Exiting.")

    nfc_config.clf.close()


if __name__ == "__main__":
    main()
