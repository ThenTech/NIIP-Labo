import struct
from os import path
from controller import Controller
from bits import Bits

DEBUG = True


class InputControllerException(Exception):
    pass

class InputController:
    """Warning: uses linux raw file input stream for joysticks!"""
    STRUCT_PACK = "IhBB"
    EVENT_SIZE  = struct.calcsize(STRUCT_PACK)
    DEVICES     = "/proc/bus/input/devices"

    AXIS_MAX = 32767  # ((1 << 15) - 1)

    # CTRL_MAP = {
    #     0: Controller.A,
    #     1: Controller.B,
    #     2: Controller.X,
    #     3: Controller.Y,

    #     4: Controller.LSHOULDER,
    #     5: Controller.RSHOULDER,

    #     6: Controller.BACK,
    #     7: Controller.START,

    #     8: Controller.LTHUMB,
    #     9: Controller.RTHUMB
    # }

    CTRL_MAP = {
        0: Controller.A,
        1: Controller.B,
        3: Controller.X,
        4: Controller.Y,

        6: Controller.LSHOULDER,
        7: Controller.RSHOULDER,

        10: Controller.BACK,
        11: Controller.START,

        13: Controller.LTHUMB,
        14: Controller.RTHUMB
    }

    def __init__(self, ctrl_name="Xbox Wireless Controller", infile="/dev/input/"):
        self.stream = None

        joystick = self._search_controller(ctrl_name)
        infile = infile + joystick

        if not path.exists(infile):
            raise InputControllerException("[InputController] Inputstream '{0}' not available?".format(infile))
        self.stream = open(infile, "rb")

        self.dpad_X_last = None
        self.dpad_Y_last = None

    def __del__(self):
        if self.stream:
            self.stream.close()

    def _search_controller(self, ctrl_name):
        # cat /proc/bus/input/devices
        joystick = "js1"

        if not path.exists(InputController.DEVICES):
            raise InputControllerException("[InputController] No input devices?")

        with open(InputController.DEVICES, "r") as devices:
            all_devs = devices.read()
            name = "N: Name=\"{}\"".format(ctrl_name)

            if name not in all_devs:
                raise InputControllerException("[InputController] No connected controller '{0}' found!".format(ctrl_name))

            first, second = all_devs.split(name, 1)

            if second and "H: Handlers=" in second:
                second = second.split("\n")
                for line in second:
                    if "H: Handlers=" in line:
                        if "js" in line:
                            line = line.split()
                            joystick = list(filter(lambda s: "js" in s, line))[0]
                            self._log("Found '{0}',  with joystick mapper '{1}'!".format(ctrl_name, joystick))
                        else:
                            raise InputControllerException("[InputController] Found '{0}', but no joystick mapper!".format(ctrl_name))
            else:
                raise InputControllerException("[InputController] No connected controller '{0}' found!".format(ctrl_name))

        return joystick

    def _log(self, msg):
        if DEBUG:
            print("[InputController] {0}".format(msg))

    def state(self, value):
        return Bits.str_to_bytes(Controller.State.ON if value else \
                                 Controller.State.OFF)

    def _handle_btn(self, code, value):
        if not code in InputController.CTRL_MAP:
            raise InputControllerException("[InputController] Button with code {0} not implemented!".format(code))

        topic, value = InputController.CTRL_MAP[code], self.state(value)

        self._log("BUTTON to topic '{0}': {1}".format(topic, value))
        return topic, value

    def _handle_dpad(self, code, value):
        topic = ""
        if code == 6:
            if value < 0:
                topic = self.dpad_X_last = Controller.DPAD_LEFT
                value = 1
            elif value > 0:
                topic = self.dpad_X_last = Controller.DPAD_RIGHT
                value = 1
            else:
                topic = self.dpad_X_last
                self.dpad_X_last = None
        elif code == 7:
            if value < 0:
                topic = self.dpad_Y_last = Controller.DPAD_UP
                value = 1
            elif value > 0:
                topic = self.dpad_Y_last = Controller.DPAD_DOWN
                value = 1
            else:
                topic = self.dpad_Y_last
                self.dpad_Y_last = None

        value = self.state(value)
        self._log("DPAD to topic '{0}': {1}".format(topic, value))
        return topic, value

    def _handle_trigger(self, code, value):
        # scale to 0..255
        value += InputController.AXIS_MAX
        value = int(value / (InputController.AXIS_MAX * 2) * 255)
        topic = ""

        if code == 5:
            topic = Controller.LT
        elif code == 4:
            topic = Controller.RT

        self._log("TRIGGER to topic '{0}': {1}".format(topic, value))
        return topic, Bits.pack(value, 1)

    def _handle_axis(self, code, value):
        topic = ""

        if code == 0:
            topic = Controller.LSTICK_X
        elif code == 1:
            topic = Controller.LSTICK_Y
        elif code == 2:
            topic = Controller.RSTICK_X
        elif code == 3:
            topic = Controller.RSTICK_Y

        self._log("AXIS to topic '{0}': {1}".format(topic, value))
        return topic, Bits.pack(value, 4, signed=True)

    def read_loop(self, callback=None):
        while True:
            topic, value = self.read_next()

            if callback:
                callback(topic, value)

            # if not topic and not value:
            #     break

    def read_next(self):
        event = self.stream.read(InputController.EVENT_SIZE) if self.stream else None

        if event:
            timestamp, value, type_, code = struct.unpack(InputController.STRUCT_PACK, event)

            if type_ == 1:
                # buttons (type = 1)
                return self._handle_btn(code, value)
            elif type_ == 2:
                # axis (type = 2)
                if 0 <= code <= 3:
                    # axis (code = 0, code = 1, code = 2 or code = 3)
                    return self._handle_axis(code, value)
                elif 4 <= code <= 5:
                    # triggers (code = 4 or code = 5)
                    return self._handle_trigger(code, value)
                elif 6 <= code <= 7:
                    # dpad (code = 6 or code = 7)
                    return self._handle_dpad(code, value)
                else:
                    self._log("Unknown code for type 2: {0}?".format(code))
            elif 129 <= code <= 130:
                # Device info setup: ignore
                pass
            else:
                self._log("Unknown type: {0}?".format(type_))

        return None, None

if __name__ == "__main__":
    ctrl = InputController()
    ctrl.read_loop()
