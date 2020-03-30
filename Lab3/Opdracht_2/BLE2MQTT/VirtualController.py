import pyxinput
from controller import Controller

class VirtualController:
    """https://github.com/bayangan1991/PYXInput"""

    CTRL_MAP = {
        Controller.A         : "BtnA",
        Controller.B         : "BtnB",
        Controller.X         : "BtnX",
        Controller.Y         : "BtnY",
        Controller.LT        : "TriggerL",
        Controller.RT        : "TriggerR",
        Controller.LTHUMB    : "BtnThumbL",
        Controller.RTHUMB    : "BtnThumbR",
        Controller.LSHOULDER : "BtnShoulderL",
        Controller.RSHOULDER : "BtnShoulderR",
        Controller.START     : "BtnStart",
        Controller.BACK      : "BtnBack",
        Controller.LSTICK_X  : "AxisLx",
        Controller.LSTICK_Y  : "AxisLy",
        Controller.RSTICK_X  : "AxisRx",
        Controller.RSTICK_Y  : "AxisRy",
    }

    DPAD_MAP = {
        Controller.DPAD_UP    : pyxinput.vController.DPAD_UP,
        Controller.DPAD_RIGHT : pyxinput.vController.DPAD_RIGHT,
        Controller.DPAD_DOWN  : pyxinput.vController.DPAD_DOWN,
        Controller.DPAD_LEFT  : pyxinput.vController.DPAD_LEFT,
    }

    def __init__(self):
        self.ctrl = pyxinput.vController(percent=False)
        # self.read = pyxinput.rController(1)

    def reset(self):
        """Reset all states to nominal or zero position."""
        for key in VirtualController.CTRL_MAP.values():
            self.ctrl.set_value(key, 0)
        self.ctrl.set_value("Dpad", pyxinput.vController.DPAD_OFF)

    def set_value(self, topic, value=0):
        """Set a value on the controller
            Buttons are True or False,
            Triggers are 0 to 255,
            Sticks are -32768 to 32767.
        """
        if topic in VirtualController.CTRL_MAP:
            ctrl_str = VirtualController.CTRL_MAP[topic]
            self.ctrl.set_value(ctrl_str, value)
        elif topic in VirtualController.DPAD_MAP:
            value = VirtualController.DPAD_MAP[topic] if value else \
                    pyxinput.vController.DPAD_OFF
            self.ctrl.set_value("Dpad", value)
        else:
            print("[VirtualController::set_value] Unknown topic '{0}'".format(topic))
