from machine import Pin
from machine import SPI, rng

import pycom
import time
pycom.heartbeat(False)


spi = SPI(0, mode=SPI.MASTER, baudrate=2000000, polarity=0, phase=0, pins=('P19', 'P20', 'P21'))
# spi clock on        P19 => CLK    (SHCP, shift clock)
# spi.write writes to P20 => MOSI   (serial data in)
# spi.read reads from P21 => unused

btn_pin  = Pin('P10', mode=Pin.IN, pull=Pin.PULL_DOWN)
STCP_pin = Pin('P22', mode=Pin.OUT)  # STCP storage out clk (latch)


class Dice:
    def __init__(self, spi, stopin, initial=1, maxval=20):
        super().__init__()
        self.spi     = spi
        self.stopin  = stopin
        self.initial = initial
        self.value   = initial
        self.maxval  = maxval

    def _number_to_led(self, number):
        nums = {
            -1 : 0b00000000,
            0  : 0b01011111,
            1  : 0b00000110,
            2  : 0b00111011,
            3  : 0b00101111,
            4  : 0b01100110,
            5  : 0b01101101,
            6  : 0b01111101,
            7  : 0b00000111,
            8  : 0b01111111,
            9  : 0b01101111,
        }

        return bytes([~(nums.get(number, nums[-1])) & 0xFF])

    def next(self):
        self.value = self.initial + (rng() % self.maxval)

    def byte(self):
        val1 = self._number_to_led(int(self.value % 10))
        val2 = self._number_to_led(self.value // 10)
        return val1 + val2

    def display(self):
        # print("Rolled: {0}".format(self.value))
        self.stopin(False)
        self.spi.write(self.byte())
        self.stopin(True)


dice = Dice(spi, STCP_pin, 0, 99)
print("start")

while(True):
    btn_val = btn_pin() # get value, 0 or 1
    dice.next()

    # Continuously shift to next value until btn pressed
    if btn_val == 1:
        print("Rolled the dice!")
        pycom.rgbled(0x1000)
        time.sleep(0.1)

        delay = 0.01
        while delay < 0.8:
            dice.display()
            time.sleep(delay)
            delay *= 1.3
            dice.next()

        dice.display()
        print("Rolled: {0}".format(dice.value))
        time.sleep(0.3)
        pycom.rgbled(0)
