import struct
from controller import Controller

AXIS_MAX = 32767  # ((1 << 15) - 1)

controller_dict = {
    0: Controller.A,
    1: Controller.B,
    3: Controller.X,
    4: Controller.Y,

    6: Controller.LSHOULDER,
    7: Controller.RSHOULDER,

    11: Controller.START,

    13: Controller.LTHUMB,
    14: Controller.RTHUMB
}

def handle_btn(code, val):
    try:
        topic = controller_dict[code]
        print("Publish '" + str(val) + "' to topic: " + str(topic))
    except:
        print("Button not implemented!")

def handle_dpad(code, val):
    topic = ""
    # TODO: navragen bij den Willy
    if code == 6:
        if val < 0:
            topic = Controller.DPAD_LEFT
        elif val > 0:
            topic = Controller.DPAD_RIGHT
        else:
            topic = Controller.DPAD_X_RESET

    if code == 7:
        if val < 0:
            topic = Controller.DPAD_UP
        elif val > 0:
            topic = Controller.DPAD_DOWN
        else:
            topic = Controller.DPAD_Y_RESET

    print("Publish '" + str(abs(val)) + "' to topic: " + topic)

def handle_trigger(code, val):
    # scale to 0..255
    val = val + AXIS_MAX
    factor = 255 / (AXIS_MAX * 2)
    val = int(val * factor)

    if code == 5:
        print("Publish '" + str(val) + "' to topic: " + Controller.LT)
    if code == 4:
        print("Publish '" + str(val) + "' to topic: " + Controller.RT)

def handle_axis(code, val):
    topic = ""
    if code == 0:
        topic = Controller.LSTICK_X
    if code == 1:
        topic = Controller.LSTICK_Y
    if code == 2:
        topic = Controller.RSTICK_X
    if code == 3:
        topic = Controller.RSTICK_Y

    print("Publish '" + str(abs(val)) + "' to topic: " + topic)



infile_path = "/dev/input/js1"
EVENT_SIZE = struct.calcsize("IhBB")
infile = open(infile_path, "rb")

event = infile.read(EVENT_SIZE)

while event:
    #print(struct.unpack("IhBB", event))
    (time, value, type_, code) = struct.unpack("IhBB", event)

    if type_ == 1:
        # buttons (type = 1)
        handle_btn(code, value)
    elif type_ == 2:
        # axis (type = 2)
        if 0 <= code <= 3:
            # axis (code = 0, code = 1, code = 2 or code = 3)
            handle_axis(code, value)
        elif 4 <= code <= 5:
            # triggers (code = 4 or code = 5)
            handle_trigger(code, value)
        elif 6 <= code <= 7:
            # dpad (code = 6 or code = 7)
            handle_dpad(code, value)
        else:
            print("Unknown code for type 2: {0}?".format(code))
    else:
        print("Unknown type: {0}?".format(type_))

    event = infile.read(EVENT_SIZE)
