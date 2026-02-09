#!/usr/bin/python3

# mpvserial.py
# This script runs at boot on the Raspberry Pi and connects to a Unix socket
# created by mpv --input-ipc-server=/tmp/mpvsocket. It listens to messages
# written to the Raspberry Pi's serial UART using pySerial and issues commands
# to the mpv IPC if they match a file name or other command.
# https://mpv.io/manual/master/#json-ipc

# This file is in the public domain (Unlicense). https://unlicense.org

import json
import os
import socket
import time

import serial


def send_command(command):
    msg = json.dumps(command).encode() + b"\n"
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect("/tmp/mpvsocket")
                client.send(msg)
                break
        except ConnectionRefusedError:
            print("Retrying connection to socket...")
            time.sleep(1)


def main():
    ser = serial.Serial("/dev/serial0", baudrate=115200, timeout=1)

    while True:
        try:
            line = ser.readline().decode(encoding="utf-8", errors="ignore").strip()
            if not line:
                continue

            if line == "_reset":
                send_command({"command": ["loadfile", "/home/pi/Pictures/idle/"]})
            elif line == "_quit":
                send_command({"command": ["quit"]})
                ser.close()
                time.sleep(1)
                os.system("systemctl poweroff")
                break
            else:
                filepath = "/home/pi/Pictures/games/" + line + ".png"
                if os.path.exists(filepath):
                    send_command({"command": ["loadfile", filepath]})
                else:
                    print(f"Invalid command: {line}")

        except KeyboardInterrupt:
            ser.close()
            send_command({"command": ["quit"]})
            break


if __name__ == "__main__":
    main()
