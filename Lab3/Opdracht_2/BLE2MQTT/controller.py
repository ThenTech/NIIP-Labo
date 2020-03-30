import pyxinput
from bits import Bits

class Controller:
    """
        Buttons/DPAD are [False, True],
        Triggers are [0, 255],
        Sticks are [-32768, 32767]
    """
    X         = "button/X"
    Y         = "button/Y"
    A         = "button/A"
    B         = "button/B"
    LT        = "button/trigger/left"
    RT        = "button/trigger/right"
    LTHUMB    = "button/thumb/left"
    RTHUMB    = "button/thumb/right"
    LSHOULDER = "button/shoulder/left"
    RSHOULDER = "button/shoulder/right"

    LSTICK_X = "stick/left/X"
    LSTICK_Y = "stick/left/Y"

    RSTICK_X = "stick/right/X"
    RSTICK_Y = "stick/right/Y"

    DPAD_UP      = "dpad/up"
    DPAD_RIGHT   = "dpad/right"
    DPAD_DOWN    = "dpad/down"
    DPAD_LEFT    = "dpad/left"

    DPAD_X_RESET = "dpad/x_reset"
    DPAD_Y_RESET = "dpad/y_reset"

    START = "button/start"
    BACK  = "button/back"

    class State:
        ON  = "ON"
        OFF = "OFF"

    class All:
        BUTTONS   = "button/#"
        TRIGGERS  = "button/trigger/#"
        THUMBS    = "button/thumb/#"
        SHOULDERS = "button/shoulder/#"

        STICKS = "stick/#"
        LSTICK = "stick/left/#"
        RSTICK = "stick/right/#"

        DPAD = "dpad/#"

    @staticmethod
    def values():
        return list(filter(lambda s: isinstance(s, str) \
                                 and not s.startswith("__") \
                                 and not "controller" in s,
                           Controller.__dict__.values()))



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

    _DPAD_MAP_IDX = {
        pyxinput.vController.DPAD_UP    : 0,  # 1
        pyxinput.vController.DPAD_RIGHT : 3,  # 8
        pyxinput.vController.DPAD_DOWN  : 1,  # 2
        pyxinput.vController.DPAD_LEFT  : 2,  # 4
    }

    def __init__(self):
        self.ctrl = pyxinput.vController(percent=False)
        # self.read = pyxinput.rController(1)
        self.dpad_mask = pyxinput.vController.DPAD_OFF

    def _dpad_set(self, mask=0, value=0):
        if mask == pyxinput.vController.DPAD_OFF:
            # 0 == Off
            self.dpad_mask = mask
        else:
            idx = VirtualController._DPAD_MAP_IDX[mask]
            self.dpad_mask = Bits.set(self.dpad_mask, idx, 1 if value else 0)

    def reset(self):
        """Reset all states to nominal or zero position."""
        for key in VirtualController.CTRL_MAP.values():
            self.ctrl.set_value(key, 0)
        self._dpad_set(pyxinput.vController.DPAD_OFF)
        self.ctrl.set_value("Dpad", self.dpad_mask)

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
            mask = VirtualController.DPAD_MAP[topic]
            self._dpad_set(mask, value)
            self.ctrl.set_value("Dpad", self.dpad_mask)
        else:
            print("[VirtualController::set_value] Unknown topic '{0}'".format(topic))
