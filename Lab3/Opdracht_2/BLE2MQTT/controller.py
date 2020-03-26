class Controller:
    X  = "button/X"
    Y  = "button/Y"
    A  = "button/A"
    B  = "button/B"
    LT = "trigger/left"
    RT = "trigger/right"

    LSTICK_UP    = "stick/left/up"
    LSTICK_RIGHT = "stick/left/right"
    LSTICK_DOWN  = "stick/left/down"
    LSTICK_LEFT  = "stick/left/left"

    RSTICK_UP    = "stick/right/up"
    RSTICK_RIGHT = "stick/right/right"
    RSTICK_DOWN  = "stick/right/down"
    RSTICK_LEFT  = "stick/right/left"

    DPAD_UP      = "dpad/up"
    DPAD_RIGHT   = "dpad/right"
    DPAD_DOWN    = "dpad/down"
    DPAD_LEFT    = "dpad/left"

    START  = "button/start"
    SELECT = "button/select"

    class State:
        ON  = "ON"
        OFF = "OFF"

    class All:
        BUTTONS  = "button/#"
        TRIGGERS = "trigger/#"

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
