# update.pyw
# Part of Lutero. https://github.com/TheOpponent/Lutero
# This file is in the public domain (Unlicense). https://unlicense.org

# For publishing commands targeting a networked digital signage device running
# mpvlisten.py on the "lutero/sign" topic. 
# This script assumes the MQTT broker is on the same local network and accepts
# anonymous connections.

# Uses paho-mqtt.

import sys

from paho.mqtt import publish

# Set to the IP of the PC running the MQTT broker. Ideally this will be this
# PC, with the listener setting bound to the IP of the NIC (not localhost)
# connected to the digital sign or hub.
BROKER_IP = "192.168.19.1"
BROKER_PORT = 1883

def main():
    if len(sys.argv) == 1:
        publish.single("lutero/sign", "^reset", 2, False, BROKER_IP, BROKER_PORT)
    elif len(sys.argv) == 2:
        publish.single("lutero/sign", sys.argv[1], 2, False, BROKER_IP, BROKER_PORT)
    else:
        print("Incorrect number of arguments.")
        sys.exit()


if __name__ == "__main__":
    main()
