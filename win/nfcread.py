# nfcread.py
# Uses nfcpy to drive an NFC tag reader to continuously scan for
# supported tags. Commands can be executed based on tag IDs.

# This file is in the public domain (Unlicense). https://unlicense.org

import tomllib
import subprocess
import time

import nfc
from serial import SerialException


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
                print(f"{nfc_config.driver} NFC reader on COM{nfc_config.com_port} opened.")
                nfc_config.connected = True
                return
            except SerialException:
                if not serial_error_message:
                    print(f"No {nfc_config.driver} NFC reader detected on COM{nfc_config.com_port}. Waiting until it becomes available.")
                    serial_error_message = True
                time.sleep(1)
    else:
        print("Autodetecting NFC reader.")
        while True:
            result = nfc_config.clf.open("com")
            if result and nfc_config.clf.device is not None:
                print(f"{nfc_config.driver} NFC reader on {nfc_config.clf.device.path} opened.")
                nfc_config.connected = True
                return
            else:
                time.sleep(1)


def main():
    try:
        with open("nfcread.toml","rb") as nfc_toml_file:
            nfc_toml = tomllib.load(nfc_toml_file)
    except IOError:
        print("nfcread.toml not found.")
        exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"Error reading nfcread.toml: {e}")
        exit(1)

    nfc_config = NFCConfig()

    nfc_config.com_port = str(nfc_toml['reader']['com_port'])
    nfc_config.driver = nfc_toml['reader']['driver']
    nfc_config.remove_timeout = nfc_toml['reader']['remove_timeout']

    tag_commands = nfc_toml['tag_commands']

    remove_timeout = 0
    current_tag = None
    command = None
    old_command = None
    log_new_tags = nfc_toml['reader']['log_new_tags']
    new_tags_file_write_error = False
    new_tags = set()

    while True:
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
                                with open("new_tags.txt","a") as file:
                                    file.write(tag_id + "\n")
                            except IOError:
                                new_tags_file_write_error = True
                                print("Error writing to new_tags.txt. New tag ID(s) will be written to console when the program exits.")
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
                            print(f"Tag removed. Waiting {nfc_config.remove_timeout} seconds before executing exit action.")
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
            print(f"Error writing to new_tags.txt. {len(new_tags)} new tag ID(s) listed below:")
            for i in new_tags:
                print(i)
            

    print("Exiting.")

    nfc_config.clf.close()


if __name__ == "__main__":
    main()
