# update.py
# Issues a command to the Raspberry Pi digital sign's serial UART using
# pySerial to load an image with a filename that matches the first
# argument. If no arguments are provided, send a command to the
# digital sign to load the idle images collection instead.

# This file is in the public domain (Unlicense). https://unlicense.org

import sys

import serial

# Set this to the serial port of your USB to TTL device.
SERIAL_PORT = "COM1"

ser = serial.Serial(SERIAL_PORT, baudrate=115200, timeout=1)

# If a game name is given as the first command line argument, set the
# display to that game.
if len(sys.argv) > 1:
    ser.write(sys.argv[1].encode())
else:
    # If run without arguments, set the digital sign to the idle
    # collection.
    ser.write("_reset".encode())
ser.close()
