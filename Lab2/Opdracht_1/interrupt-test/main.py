import pycom
import time
import machine

import network
from machine import I2C, Pin

from mcp9808 import *

DEBUG = True
WITH_SENSOR = False

ALERT_PIN = "P13"
TMP_THRESHOLD = 2600


def on_error(self, msg=""):
    pycom.rgbled(0xFF0000)
    print("Error: " + msg)
    time.sleep(5)

def get_self_temperature():
    return int((machine.temperature() - 32) * 100 / 1.8)

def go_to_sleep():
    print("Going to sleep...")
    # machine.deepsleep(5000)
    # machine.deepsleep()
    machine.sleep()


# Main
if __name__ == "__main__":
    print("Boot")

    rst = machine.reset_cause()

    if rst != machine.DEEPSLEEP_RESET:
        # Normal reset, not from being awoken
        print("Wake on RESET")

        # Configure as fire sensor
        pycom.heartbeat(False)
        pycom.wifi_on_boot(False)

        # If first boot, get settings from remote
        if WITH_SENSOR:
            i2c    = I2C(0, I2C.MASTER, baudrate=100000)
            tsense = MCP9808(i2c)

            tsense.set_alert_mode(enable_alert=True,
                                output_mode=ALERT_OUTPUT_INTERRUPT,
                                polarity=ALERT_POLARITY_ALOW,
                                selector=ALERT_SELECT_CRIT)
            tsense.set_alert_boundary_temp(REG_TEMP_BOUNDARY_CRITICAL,
                                        TMP_THRESHOLD / 100.0)

        alert_pin = Pin(ALERT_PIN, mode=Pin.IN, pull=Pin.PULL_UP)
        machine.pin_sleep_wakeup((ALERT_PIN,), machine.WAKEUP_ALL_LOW, enable_pull=True)

        go_to_sleep()
    else:
        # Recover from deepsleep
        reason = machine.wake_reason()[0]

        if reason == machine.PIN_WAKE:
            print("Wake on PIN_INTERRUPT")

            if WITH_SENSOR:
                i2c    = I2C(0, I2C.MASTER, baudrate=100000)
                tsense = MCP9808(i2c)

                tsense.acknowledge_alert_irq()  # Is this needed in this case?
                measurement = int(tsense.get_temp() * 100)

                print("Temp = {0} >= {1}".format(measurement, TMP_THRESHOLD))
                if measurement >= TMP_THRESHOLD:
                    print("Too hot for comfort!")
                else:
                    print("Comfortable temperature.")

            time.sleep(5)

            alert_pin = Pin(ALERT_PIN, mode=Pin.IN, pull=Pin.PULL_UP)
            machine.pin_sleep_wakeup((ALERT_PIN,), machine.WAKEUP_ALL_LOW, enable_pull=True)

            go_to_sleep()
        else:
            print("Wake on ???")
