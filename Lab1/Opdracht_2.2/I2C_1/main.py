import pycom
import time

from machine import I2C
from mcp9808 import MCP9808


# Main
if __name__ == "__main__":
    # Disable heartbeat
    pycom.heartbeat(False)

    i2c = I2C(0, I2C.MASTER, baudrate=100000)
    tsense = MCP9808(i2c)

    while True:
        print("Temperature: {0:.2f}°C".format(tsense.get_temp()))
        time.sleep(0.5)
