
# Resolution settings
HALF_C      = 0x0
QUARTER_C   = 0x1
EIGHTH_C    = 0x2
SIXTEENTH_C = 0x3

class MCP9808:
    """
    Interface to the MCP9808 temperature sensor.
    https://cdn-shop.adafruit.com/datasheets/MCP9808.pdf
    """

    def __write(self, data):
        self.i2c.writeto(self.address, data)

    def __writemem(self, memaddr, data):
        self.i2c.writeto_mem(self.address, memaddr, data)

    def __read(self, size):
        return self.i2c.readfrom(self.address, size)

    def __readmem(self, memaddr, size):
        return self.i2c.readfrom_mem(self.address, memaddr, size)


    # Address: `0011 A2 A1 A0 + R/W`
    def __init__(self, i2c_bus, address=0x18):
        self.i2c     = i2c_bus
        self.address = address

        self.buf     = bytearray(3)
        self.is_ok   = False

    def is_available(self):
        if not self.is_ok:
            for addr in self.i2c.scan():
                if addr == self.address:
                    # Check manufacturer and device ids
                    self.buf = self.__readmem(0x06, 2)
                    if self.buf[0] == 0 and self.buf[1] == 0x54:
                        # Correct
                        self.buf = self.__readmem(0x07, 2)
                        self.is_ok = self.buf[0] == 0x04
                        if self.is_ok: break
        return self.is_ok

    @property
    def temperature(self):
        """Temperature in celsius. Read-only."""
        if not self.is_ok and not self.is_available():
            return -1

        self.buf = self.__readmem(0x05, 2)

        # Get value
        sign        = self.buf[0] & 0x10 > 0
        measurement = float((self.buf[0] & 0xF) * 4.0) + float(self.buf[1]) / 16.0

        return 256 - measurement if sign else measurement
