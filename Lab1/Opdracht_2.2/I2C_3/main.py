import pycom
import time

from machine import I2C
from mcp9808 import MCP9808
from pca9632 import PCA9632, LEDColour, LEDColourDefault


class Switch(dict):
    """Custom class to act as switch case like structure for dicts."""
    def __getitem__(self, item):
        for key in self.keys():                   # iterate over the intervals
            if item in key:                       # if the argument is part of that interval
                return super().__getitem__(key)   # return its associated value
        raise KeyError(item)

    def get(self, item, default=None):
        for key in self.keys():
            if item in key:
                return super().__getitem__(key)
        return default

class Range():
    """Custom class to act as range() key for LUT."""
    def __init__(self, start, stop):
        self.start = start
        self.stop  = stop

    def __contains__(self, key):
        return self.start <= key < self.stop

    def __key(self):
        return (self.start, self.stop)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Range):
            return self.__key() == other.__key()
        return NotImplemented

# Ambient colour range LUT
# range contains temperature in Celsius * 100 (int)
ambient_colours = Switch({
    Range(   8778, 10000) : LEDColour.from_hex("0xFF0EF000"),
    Range(   8667,  8778) : LEDColour.from_hex("0xFF0DF000"),
    Range(   8556,  8667) : LEDColour.from_hex("0xFF0CF000"),
    Range(   8444,  8556) : LEDColour.from_hex("0xFF0BF000"),
    Range(   8333,  8444) : LEDColour.from_hex("0xFF0AF000"),
    Range(   8222,  8333) : LEDColour.from_hex("0xFF09F000"),
    Range(   8111,  8222) : LEDColour.from_hex("0xFF08F000"),
    Range(   8000,  8111) : LEDColour.from_hex("0xFF07F000"),
    Range(   7889,  8000) : LEDColour.from_hex("0xFF06F000"),
    Range(   7778,  7889) : LEDColour.from_hex("0xFF05F000"),
    Range(   7667,  7778) : LEDColour.from_hex("0xFF04F000"),
    Range(   7556,  7667) : LEDColour.from_hex("0xFF03F000"),
    Range(   7444,  7556) : LEDColour.from_hex("0xFF02F000"),
    Range(   7333,  7444) : LEDColour.from_hex("0xFF01F000"),
    Range(   7222,  7333) : LEDColour.from_hex("0xFF00F000"),
    Range(   7111,  7222) : LEDColour.from_hex("0xFF00E000"),
    Range(   7000,  7111) : LEDColour.from_hex("0xFF00D000"),
    Range(   6889,  7000) : LEDColour.from_hex("0xFF00C000"),
    Range(   6778,  6889) : LEDColour.from_hex("0xFF00B000"),
    Range(   6667,  6778) : LEDColour.from_hex("0xFF00A000"),
    Range(   6556,  6667) : LEDColour.from_hex("0xFF009000"),
    Range(   6444,  6556) : LEDColour.from_hex("0xFF008000"),
    Range(   6333,  6444) : LEDColour.from_hex("0xFF007000"),
    Range(   6222,  6333) : LEDColour.from_hex("0xFF006000"),
    Range(   6111,  6222) : LEDColour.from_hex("0xFF005000"),
    Range(   6000,  6111) : LEDColour.from_hex("0xFF004000"),
    Range(   5889,  6000) : LEDColour.from_hex("0xFF003000"),
    Range(   5778,  5889) : LEDColour.from_hex("0xFF002000"),
    Range(   5667,  5778) : LEDColour.from_hex("0xFF001000"),
    Range(   5556,  5667) : LEDColour.from_hex("0xFF000000"),
    Range(   5444,  5556) : LEDColour.from_hex("0xFF0a0000"),
    Range(   5333,  5444) : LEDColour.from_hex("0xFF140000"),
    Range(   5222,  5333) : LEDColour.from_hex("0xFF1e0000"),
    Range(   5111,  5222) : LEDColour.from_hex("0xFF280000"),
    Range(   5000,  5111) : LEDColour.from_hex("0xFF320000"),
    Range(   4889,  5000) : LEDColour.from_hex("0xFF3c0000"),
    Range(   4778,  4889) : LEDColour.from_hex("0xFF460000"),
    Range(   4667,  4778) : LEDColour.from_hex("0xFF500000"),
    Range(   4556,  4667) : LEDColour.from_hex("0xFF5a0000"),
    Range(   4444,  4556) : LEDColour.from_hex("0xFF640000"),
    Range(   4333,  4444) : LEDColour.from_hex("0xFF6e0000"),
    Range(   4222,  4333) : LEDColour.from_hex("0xFF780000"),
    Range(   4111,  4222) : LEDColour.from_hex("0xFF820000"),
    Range(   4000,  4111) : LEDColour.from_hex("0xFF8c0000"),
    Range(   3889,  4000) : LEDColour.from_hex("0xFF960000"),
    Range(   3778,  3889) : LEDColour.from_hex("0xFFa00000"),
    Range(   3667,  3778) : LEDColour.from_hex("0xFFaa0000"),
    Range(   3556,  3667) : LEDColour.from_hex("0xFFb40000"),
    Range(   3444,  3556) : LEDColour.from_hex("0xFFbe0000"),
    Range(   3333,  3444) : LEDColour.from_hex("0xFFc80000"),
    Range(   3222,  3333) : LEDColour.from_hex("0xFFd20000"),
    Range(   3111,  3222) : LEDColour.from_hex("0xFFdc0000"),
    Range(   3000,  3111) : LEDColour.from_hex("0xFFe60000"),
    Range(   2889,  3000) : LEDColour.from_hex("0xFFf00000"),
    Range(   2778,  2889) : LEDColour.from_hex("0xFFfa0000"),
    Range(   2667,  2778) : LEDColour.from_hex("0xfdff0000"),
    Range(   2556,  2667) : LEDColour.from_hex("0xd7ff0000"),
    Range(   2444,  2556) : LEDColour.from_hex("0xb0ff0000"),
    Range(   2333,  2444) : LEDColour.from_hex("0x8aff0000"),
    Range(   2222,  2333) : LEDColour.from_hex("0x65ff0000"),
    Range(   2111,  2222) : LEDColour.from_hex("0x3eff0000"),
    Range(   2000,  2111) : LEDColour.from_hex("0x17ff0000"),
    Range(   1889,  2000) : LEDColour.from_hex("0x00ff1000"),
    Range(   1778,  1889) : LEDColour.from_hex("0x00ff3600"),
    Range(   1667,  1778) : LEDColour.from_hex("0x00ff5c00"),
    Range(   1556,  1667) : LEDColour.from_hex("0x00ff8300"),
    Range(   1444,  1556) : LEDColour.from_hex("0x00ffa800"),
    Range(   1333,  1444) : LEDColour.from_hex("0x00ffd000"),
    Range(   1222,  1333) : LEDColour.from_hex("0x00fff400"),
    Range(   1111,  1222) : LEDColour.from_hex("0x00e4ff00"),
    Range(   1000,  1111) : LEDColour.from_hex("0x00d4ff00"),
    Range(    889,  1000) : LEDColour.from_hex("0x00c4ff00"),
    Range(    778,   889) : LEDColour.from_hex("0x00b4ff00"),
    Range(    667,   778) : LEDColour.from_hex("0x00a4ff00"),
    Range(    556,   667) : LEDColour.from_hex("0x0094ff00"),
    Range(    444,   556) : LEDColour.from_hex("0x0084ff00"),
    Range(    333,   444) : LEDColour.from_hex("0x0074ff00"),
    Range(    222,   333) : LEDColour.from_hex("0x0064ff00"),
    Range(    111,   222) : LEDColour.from_hex("0x0054ff00"),
    Range(    000,   111) : LEDColour.from_hex("0x0044ff00"),
    Range(   -111,   000) : LEDColour.from_hex("0x0032ff00"),
    Range(   -222,  -111) : LEDColour.from_hex("0x0022ff00"),
    Range(   -333,  -222) : LEDColour.from_hex("0x0012ff00"),
    Range(   -444,  -333) : LEDColour.from_hex("0x0002ff00"),
    Range(   -556,  -444) : LEDColour.from_hex("0x0000ff00"),
    Range(   -667,  -556) : LEDColour.from_hex("0x0100ff00"),
    Range(   -778,  -667) : LEDColour.from_hex("0x0200ff00"),
    Range(   -889,  -778) : LEDColour.from_hex("0x0300ff00"),
    Range(  -1000,  -889) : LEDColour.from_hex("0x0400ff00"),
    Range(-100000, -1000) : LEDColour.from_hex("0x0500ff00"),
})


def run_test(led, start=-1000, stop=10000, step=50):
    prev_colour = LEDColourDefault.BLACK

    for measured in range(-1000, 10000, 50):
        new_colour = ambient_colours.get(measured, LEDColourDefault.BLACK)
        if new_colour.byte() != prev_colour.byte():
            prev_colour = new_colour
            led.set_colour_all(new_colour)

        time.sleep(0.03)


# Main
if __name__ == "__main__":
    i2c = I2C(0, I2C.MASTER, baudrate=100000)

    tsense = MCP9808(i2c)
    led = PCA9632(i2c)
    led.config(allcal=1, dimming=True)

    prev_colour = LEDColourDefault.BLACK

    while True:
        measured = tsense.get_temp()
        print("Temperature: {0:.2f}°C".format(measured))

        new_colour = ambient_colours.get(int(measured * 100), LEDColourDefault.BLACK)

        # Check if different to decrease I2C traffic
        if new_colour.byte() != prev_colour.byte():
            prev_colour = new_colour
            led.set_colour_all(new_colour)

        time.sleep(0.5)

    # # Test: Cycle through every colour
    # while True:
    #     run_test(led, -1000, 10000, 50)
    #     run_test(led, 10000, -1000, -50)
