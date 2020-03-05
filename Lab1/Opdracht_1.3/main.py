import pycom
from machine import Pin
import time

p_out = Pin('P5', mode=Pin.OUT)

# Main init
def init():
    # Disable heartbeat
    pycom.heartbeat(False)

# Main loop
def loop():
    p_out.value(0)
    time.sleep(1)
    p_out.value(1)
    time.sleep(1)

    return True

# Main
if __name__ == "__main__":
    init()
    while loop(): pass
