# wallpaper.pyw
# Changes the current desktop wallpaper on a Windows PC from the image files
# in a given folder. If a command line argument is provided, change the
# wallpaper to that file name in the WALLPAPER_PATH. Otherwise, change the
# wallpaper to a random image file in that path. After a 10 second delay,
# the wallpaper is changed back to the image with the first alphabetical
# file name in the WALLPAPER_PATH.
# Part of Lutero. https://github.com/TheOpponent/Lutero
# This file is in the public domain (Unlicense). https://unlicense.org

import argparse
import ctypes
import random
import sys
import time
from pathlib import Path

from playsound3 import playsound

# Set this to the default number of seconds before changing to the default
# wallpaper.
DELAY = 10
# Set this to the folder containing wallpapers (using double backslashes),
# including trailing backslashes.
WALLPAPER_PATH = "..\\wallpaper\\"
# Set this to an image file to reset to after the delay.
DEFAULT_WALLPAPER = "..\\wallpaper\\000.png"


def change_wallpaper(image_path: str):
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
    except Exception as e:
        print(f"Error changing wallpaper: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--image",
        default="",
        type=str,
        help="A JPG or PNG file to use as the wallpaper. If not specified, a random file in the wallpaper directory is used.",
    )
    parser.add_argument(
        "-s",
        "--sound",
        default="",
        type=str,
        help="An MP3 file to play when the wallpaper is changed. If not specified, a random file in the wallpaper directory is used, unless --nosound is given.",
    )
    parser.add_argument(
        "-d",
        "--delay",
        default=DELAY,
        type=int,
        help="Time in seconds to reset the wallpaper to the default. Set to 0 to not reset the wallpaper.",
    )
    parser.add_argument(
        "-ns", "--nosound", action="store_true", help="Do not play a sound."
    )
    args = parser.parse_args()

    if args.sound != "" and args.nosound:
        print("Error: Cannot set --sound and --nosound simultaneously.")
        sys.exit(1)

    images_path = Path(__file__).parent / WALLPAPER_PATH
    images = (
        list(images_path.glob("*.png"))
        + list(images_path.glob("*.jpg"))
        + list(images_path.glob("*.jpeg"))
    )
    if Path(DEFAULT_WALLPAPER) in images:
        images.remove(Path(DEFAULT_WALLPAPER))
    sounds = list(images_path.glob("*.mp3"))

    if len(images) == 0:
        print(f"Error: No images found in {images_path.resolve()}.")
        sys.exit(1)

    delay = args.delay

    if args.image == "":
        pairs = []
        for img in images:
            sound_path = Path(img).with_suffix(".mp3")
            if sound_path.exists():
                pairs.append((img, sound_path))
                sounds.remove(sound_path)
            else:
                pairs.append((img, None))

        select = random.choice(pairs)
        img = select[0]
        if args.sound == "":
            if select[1] is None:
                if len(sounds) > 0:
                    snd = random.choice(sounds)
                else:
                    snd = None
            else:
                snd = select[1]
        else:
            if Path(args.sound).exists():
                snd = Path(args.sound)
            else:
                print(f"Error: Cannot find image file {Path(args.sound).resolve()}.")
                sys.exit(1)

        change_wallpaper(img)

    else:
        if Path(args.image).exists():
            change_wallpaper(args.image)
        else:
            print(f"Error: Cannot find image file {Path(args.image).resolve()}.")

        if args.sound != "":
            if Path(args.sound).exists():
                snd = Path(args.sound)
            else:
                print(f"Error: Cannot find image file {Path(args.sound).resolve()}.")
                sys.exit(1)
        else:
            sound_path = Path(args.image).with_suffix(".mp3")
            if sound_path.exists():
                snd = sound_path
            else:
                if len(sounds) > 0:
                    snd = random.choice(sounds)
                else:
                    snd = None

    if not args.nosound and snd is not None:
        playsound(snd.resolve())

    if delay > 0:
        time.sleep(delay)
        change_wallpaper(DEFAULT_WALLPAPER)


if __name__ == "__main__":
    main()
