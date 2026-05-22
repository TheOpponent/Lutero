# Uses nfcpy to drive an NFC tag reader to continuously scan for
# supported tags and launch an associated command, and pynput to
# monitor keyboard input to launch randomly selected commands.

# This file is in the public domain (Unlicense). https://unlicense.org

import random
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
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

    lock: threading.Lock = threading.Lock()
    "A `threading.Lock` object, to safely access the button variables."

    def stop_button_listening(self):
        with self.lock:
            self.button_listening = False
            self.button_active = False

    def start_button_listening(self):
        with self.lock:
            self.button_listening = True


@dataclass
class NFCConfig:
    """Dataclass for NFC reader configuration."""

    clf: nfc.ContactlessFrontend = nfc.ContactlessFrontend()
    "`nfc.ContactlessFrontend` object for this reader."

    connected: Optional[bool] = None
    "Set to true when the reader is connected, false if it disconnected due to an error, or None on startup, before it is connected for the first time."

    com_port: str = "0"

    driver: str = ""
    "A driver supported by nfcpy."

    remove_timeout: int = 0
    "The delay after a tag is removed before the exit command is executed."


class Commands:
    """Class for dictionaries and lists of command paths."""

    def __init__(self):
        self.tag_commands: dict[str,str] = {}
        self.button_commands_src: list[str] = []
        self.button_commands: list[str] = []

    def reset_button_commands(self):
        self.button_commands = self.button_commands_src.copy()
        random.shuffle(self.button_commands)

    def get_button_command(self):
        if len(self.button_commands) == 0:
            self.reset_button_commands()
        return self.button_commands.pop()

    def get_pseudorandom_command(self,id):
        """Gets a command selected based on the id, a hex string
        converted to integer.
        """

        return list(self.tag_commands.values())[int(id,16) % len(self.tag_commands)]


def connect_nfc_reader(nfc_config: NFCConfig, blocking=True):
    """Attempt to connect to the NFC reader device.

    If the connection fails, sleeps for 1 second.
    If blocking is True, repeat until a connection is established,
    otherwise return False after 1 second.
    """
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
                return True
            except SerialException:
                if not serial_error_message:
                    print(
                        f"No {nfc_config.driver} NFC reader detected on COM{nfc_config.com_port}. Waiting until it becomes available."
                    )
                    serial_error_message = True
                time.sleep(1)
                if not blocking:
                    return False
    else:
        print("Autodetecting NFC reader.")
        while True:
            result = nfc_config.clf.open("com")
            if result and nfc_config.clf.device is not None:
                print(
                    f"{nfc_config.driver} NFC reader on {nfc_config.clf.device.path} opened."
                )
                nfc_config.connected = True
                return True
            else:
                time.sleep(1)
                if not blocking:
                    return False


def get_command_path(path, prefix="programs") -> str:
    """Get the resolved, absolute path of a given command.

    If the path is already absolute, return the same path as a string.
    Otherwise, add the prefix to the path and return that as a string.
    """

    p = Path(path)
    try:
        if p.is_absolute():
            return str(p.resolve(strict=True))
        else:
            return str((Path(prefix) / p).resolve(strict=True))
    except OSError as e:
        print(f"Error with command {path}: {e}")
        raise e


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


def update_tags(commands: Commands, exit_on_error=False):
    try:
        with open("config.toml", "rb") as config_file:
            config = tomllib.load(config_file)
    except IOError:
        print("Error: config.toml not found.")
        if exit_on_error:
            exit(1)
        return False
    except tomllib.TOMLDecodeError as e:
        print(f"Error reading config.toml: {e}")
        if exit_on_error:
            exit(1)
        return False

    commands.tag_commands = config["tag_commands"]
    if len(commands.tag_commands) == 0 and config["reader"]["nfc_enabled"]:
        print("Error: No button commands available.")
        if exit_on_error:
            exit(1)

    if config["button"]["whitelist"]:
        commands.button_commands_src = config["button"]["whitelist_commands"]
    else:
        commands.button_commands_src = config["tag_commands"].values()
    if config["button"]["blacklist"]:
        button_commands_blacklist = config["button"]["blacklist_commands"]
        commands.button_commands_src = [
            i for i in commands.button_commands_src if i not in button_commands_blacklist
        ]
    if len(commands.button_commands_src) == 0 and config["button"]["button_enabled"]:
        print("Error: No button commands available.")
        if exit_on_error:
            exit(1)
        return False
    commands.reset_button_commands()

    # TODO: Graphical validation.
    for k,v in commands.tag_commands.items():
        try:
            get_command_path(v)
        except OSError as e:
            print(f"Error with tag ID {k}: {e}")
            continue

    for c in commands.button_commands:
        try:
            get_command_path(c)
        except OSError as e:
            print(f"Error with button command {c}: {e}")


def main():

    launch_info: LaunchInfo = LaunchInfo()
    commands = Commands()

    try:
        with open("config.toml", "rb") as config_file:
            config = tomllib.load(config_file)
    except IOError:
        print("config.toml not found.")
        exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"Error reading config.toml: {e}")
        exit(1)

    if not config["reader"]["nfc_enabled"] and not config["button"]["button_enabled"]:
        print("Error: At least one of nfc_enabled or button_enabled in config.toml must be true.")
        exit(1)

    # NFC configuration.
    nfc_enabled = config["reader"]["nfc_enabled"]
    nfc_config = NFCConfig()
    nfc_config.com_port = str(config["reader"]["com_port"])
    nfc_config.driver = config["reader"]["driver"]
    nfc_config.remove_timeout = config["reader"]["remove_timeout"]
    log_new_tags = config["reader"]["log_new_tags"]

    remove_timeout = 0
    current_tag = None
    command = None
    old_command = None
    new_tags_file_write_error = False
    new_tags = set()
    pseudorandom_launch = config["reader"]["launch_pseudorandom_command_on_new_tag"]

    # Get button commands list based on whitelist/blacklist settings.
    button_enabled = config["button"]["button_enabled"]
    try:
        button_code = keyboard.Key[config["button"]["key"].lower()]
    except KeyError:
        button_code = keyboard.KeyCode.from_char(config["button"]["key"])

    if button_enabled:
        start_button_listener(launch_info, button_code)

    update_tags(commands, exit_on_error=True)

    while True:
        try:
            # Button loop.
            if button_enabled:
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
                        subprocess.Popen(get_command_path(commands.get_button_command()), shell=True)
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
            if nfc_enabled:
                try:
                    # Open the NFC device for the first time, or if it was
                    # disconnected due to an error. If attempting to reconnect,
                    # sleep for 1 second if it fails before trying again. This
                    # allows the button to still be polled during this process,
                    # albeit with a 1-second lag.
                    if not nfc_config.connected:
                        connect_nfc_reader(nfc_config, blocking=True if nfc_config.connected is None else False)

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
                            command = commands.tag_commands.get(tag_id)

                            # Launch command defined for tag ID if it exists.
                            if command is not None and old_command != command:
                                remove_timeout = nfc_config.remove_timeout
                                print(f"Executing command: {command}")
                            # Launch a pseudorandomly selected command for 
                            # non-defined tags if enabled.
                            elif command is None and pseudorandom_launch:
                                remove_timeout = nfc_config.remove_timeout
                                command = commands.get_pseudorandom_command(tag_id)
                                print(f"Executing pseudorandom command for new tag {tag_id}: {command}")
                            if command is not None and old_command != command:
                                old_command = command
                                subprocess.Popen(get_command_path(command), shell=True)
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
                                    print(f"Recorded new tag {tag_id} to new_tags.txt.")
                                elif not pseudorandom_launch:
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

    if nfc_enabled:
        nfc_config.clf.close()
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


if __name__ == "__main__":
    main()
