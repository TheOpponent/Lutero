# wallpaper.py
# Changes the current desktop wallpaper on a Windows PC from the image files
# in a given folder. If a command line argument is provided, change the
# wallpaper to that file name in the WALLPAPER_PATH. Otherwise, change the 
# wallpaper to a random image file in that path. After a 10 second delay,
# the wallpaper is changed back to the image with the first alphabetical
# file name in the WALLPAPER_PATH.

# This file is in the public domain (Unlicense). https://unlicense.org

import ctypes
from glob import glob
import random
import sys
import time

# Set this to the number of seconds before changing to the default
# wallpaper.
DELAY = 10
# Set this to the folder containing wallpapers (using double backslashes),
# including trailing backslashes.
WALLPAPER_PATH = '..\\wallpaper\\'


def change_wallpaper(image_path):
    try:
        ctypes.windll.user32.SystemParametersInfoW(20,0,image_path,3)
    except Exception as e:
        print(f"Error changing wallpaper: {e}")
        exit(1)


def main():
    files = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        files.extend(glob(WALLPAPER_PATH + ext))
    files.sort()

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = random.choice(files[1:])
    change_wallpaper(image_path)

    # Delay the change back to the default wallpaper to account for
    # loading times.
    time.sleep(DELAY)
    change_wallpaper(files[0])


if __name__ == "__main__":
    main()
