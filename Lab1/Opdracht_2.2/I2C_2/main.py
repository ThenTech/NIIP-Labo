import pycom
import time

from machine import I2C
from pca9632 import PCA9632, LEDColourDefault


# Main
if __name__ == "__main__":
    # Disable heartbeat
    pycom.heartbeat(False)
    print("start")

    i2c = I2C(0, I2C.MASTER, baudrate=100000)
    led = PCA9632(i2c)
    led.config(allcal=1, blinking=True)
    print("configured")

    idx = 0

    while True:
        # Cycle colours
        led.set_colour_all(LEDColourDefault.get(idx))
        idx += 1
        time.sleep(0.2)
