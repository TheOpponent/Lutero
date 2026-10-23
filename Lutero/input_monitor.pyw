# input_monitor.pyw
# Starts a timer that presses a keyboard key when it expires.
# Any input on any controller resets the timer.
# Part of Lutero. https://github.com/TheOpponent/Lutero
# This file is in the public domain (Unlicense). https://unlicense.org

# Uses pyglet and pynput.

import sys

import pyglet
from pyglet.input import Controller
from pynput import keyboard

# Configure settings here. TIMEOUT is in seconds.
# KEYBOARD_KEY should match the "key" setting in config.toml.
TIMEOUT = 300
KEYBOARD_KEY = "f16"


# Setup functions.
cm = pyglet.input.ControllerManager()
kb = keyboard.Controller()
try:
    key = keyboard.Key[KEYBOARD_KEY.lower()]
except KeyError:
    key = keyboard.KeyCode.from_char(KEYBOARD_KEY)


@cm.event
def on_connect(controller: Controller):
    """Open a controller object and monitor all inputs."""

    controller.open()
    controller.on_button_press = on_button_press
    controller.on_dpad_motion = on_dpad_motion
    controller.on_stick_motion = on_stick_motion
    controller.on_trigger_motion = on_trigger_motion


@cm.event
def on_disconnect(controller: Controller):
    reset_timeout()


def on_button_press(controller: Controller, button: str) -> None:
    reset_timeout()


def on_dpad_motion(controller: Controller, vector: pyglet.math.Vec2):
    reset_timeout()


def on_stick_motion(controller: Controller, stick: str, vector: pyglet.math.Vec2):
    # Apply a generous deadzone for analog sticks.
    if vector.length_squared() > 0.1:
        reset_timeout()


def on_trigger_motion(controller: Controller, trigger: str, value: float):
    reset_timeout()


# Events.
if controllers := cm.get_controllers():
    for i in controllers:
        on_connect(i)


def timeout(dt):
    kb.tap(key)
    sys.exit()


def reset_timeout():
    pyglet.clock.unschedule(timeout)
    pyglet.clock.schedule_once(timeout, TIMEOUT)


reset_timeout()

pyglet.app.run()
