#!/usr/bin/python3

# mpvlisten.py
# Part of Lutero. https://github.com/TheOpponent/Lutero
# This file is in the public domain (Unlicense). https://unlicense.org

# Runs on a Raspberry Pi or similar low-power device running mpv acting as 
# digital signage, to drive the currently displayed media using MQTT messages 
# on the "lutero/sign" topic. While the script is written for Linux, it can be 
# adapted for any platform that supports mpv and mpvsocket.
# This script runs at boot connects to a Unix socket created by
# mpv --input-ipc-server=/tmp/mpvsocket.
# It assumes the MQTT broker is on the same local network and accepts anonymous
# connections.

# Special commands include:
# "^reset" - Unsets the current image and returns to an idle loop.
# "^quit" - Shuts the Raspberry Pi down.

# Uses paho-mqtt.

import datetime
import json
import os
import socket
import time

import paho.mqtt.client as paho

# Set to the IP of the PC running the MQTT broker. Ideally this will be the
# same PC running the games, with the listener setting bound to the IP of the
# NIC connected to the digital sign or hub.
BROKER_IP = "192.168.19.1"
BROKER_PORT = 1883

# Set to path for the idle loop. This can be a single file or a directory with
# multiple files, which will be loaded as a playlist. Use mpv config or command
# line options to control how directories are loaded (e.g. shuffle, still image
# duration).
IDLE_PATH = "/home/pi/Pictures/idle/"

# Set to path for game-specific media. Use {title} where the game name will be
# substituted, which is included in the MQTT message. The default setting 
# will use PNG files for all games, but this can be replaced with a different
# file type. To use different types per file, the MQTT message must include the
# complete file name with extension for all games, and no extension used here.
GAME_MEDIA_PATH = "/home/pi/Pictures/games/{title}.png"


def send_command(command):
    """Issue a command to the mpvsocket based on the MQTT message."""

    msg = json.dumps(command).encode() + b"\n"
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client: # type: ignore
                client.connect("/tmp/mpvsocket")
                client.send(msg)
                break
        except ConnectionRefusedError:
            print("Retrying connection to socket...")
            time.sleep(1)


def on_connect(client, userdata, flags, rc):
    print(
        f"Connected to broker on {datetime.datetime.now(tz=datetime.UTC).astimezone()}."
    )
    client.subscribe("lutero/sign", 1)


def on_disconnect(client, userdata, flags):
    print(
        f"Lost connection to broker on {datetime.datetime.now(tz=datetime.UTC).astimezone()}. Reconnecting..."
    )


def on_message(client, userdata, msg):
    line = msg.payload.decode()
    print(line)
    if line == "^reset":
        send_command({"command": ["loadfile", IDLE_PATH]})
    elif line == "^quit":
        send_command({"command": ["quit"]})
        time.sleep(1)
        os.system("systemctl poweroff")
    else:
        send_command(
            {"command": ["loadfile", GAME_MEDIA_PATH.format(title=line)]}
        )


def main():
    client = paho.Client()
    client.user_data_set([])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=8)

    print(f"Connecting to broker at {BROKER_IP}:{BROKER_PORT}.")
    client.connect_async(BROKER_IP, BROKER_PORT)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
