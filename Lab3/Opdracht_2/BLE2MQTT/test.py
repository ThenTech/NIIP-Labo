from evdev import InputDevice, categorize, ecodes, events
from controller import Controller

CENTER_TOLERANCE = 350
STICK_MAX = 65536

controller_dict = {
    304: Controller.A,
    305: Controller.B,
    307: Controller.X,
    308: Controller.Y,

    310: Controller.LSHOULDER,
    311: Controller.RSHOULDER,

    158: Controller.BACK,
    315: Controller.START,

    317: Controller.LTHUMB,
    318: Controller.RTHUMB
}
def handle_btn(code, val):
    try:
        topic = controller_dict[code]
        print("Publish '" + str(val) + "' to topic: " + str(topic))
    except:
        print("Button not implemented!")

def handle_trigger(code, val):
    val = int(val / 4);
    if code == 10:
        print("Publish '" + str(val) + "' to topic: " + Controller.LT)
    if code == 9:
        print("Publish '" + str(val) + "' to topic: " + Controller.RT)

def handle_dpad(code, val):
    topic = ""
    # TODO: navragen bij den Willy
    if code == 16:
        if val == -1:
            topic = Controller.DPAD_LEFT
        elif val == 1:
            topic = Controller.DPAD_RIGHT
        else:
            topic = Controller.DPAD_X_RESET
    
    if code == 17:
        if val == -1:
            topic = Controller.DPAD_UP
        elif val == 1:
            topic = Controller.DPAD_DOWN
        else:
            topic = Controller.DPAD_Y_RESET
    
    print("Publish '" + str(abs(val)) + "' to topic: " + topic)

def handle_axis(code, value):
    pass


gamepad = InputDevice("/dev/input/js1")

print(gamepad.capabilities()[3])

for event in gamepad.read_loop():
    if event.type == ecodes.EV_KEY:
        handle_btn(event.code, event.value)
    if event.code == 9 or event.code == 10:
        handle_trigger(event.code, event.value)
    if event.code == 16 or event.code == 17:
        handle_dpad(event.code, event.value)
    if event.code == 0 or event.code == 1 or event.code == 2 or event.code == 5:
        print(event)
        handle_axis(event.code, event.value)
    