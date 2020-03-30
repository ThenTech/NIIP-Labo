
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


