# Imports
from machine import I2C


# Helpers
def bit(idx, val, size = 1):
    val = val & ((1 << size) - 1)
    return (val << idx)

def get(val, idx, size = 1):
    return ((val >> idx) & ((1 << size) - 1))

def to_single_byte(raw):
    if isinstance(raw, bytes):
        return int(raw[0])
    return raw

# Addresses
ADDR_BASE    = const(0xC4 >> 1)
ADDR_SWRST   = const(0x06 >> 1)
ADDR_ALLCAL  = const(0xE0 >> 1)
ADDR_SUB1    = const(0xE2 >> 1)
ADDR_SUB2    = const(0xE4 >> 1)
ADDR_SUB3    = const(0xE8 >> 1)


class LED_Mode:
    OFF        = const(0b00)   # LED off
    FULL_ON    = const(0b01)   # LED always on at full brightness
    PWM_IND    = const(0b10)   # LED with individual PWM
    PWM_INDGRP = const(0b11)   # LED with individual and group PWM

    _All = (OFF, FULL_ON, PWM_IND, PWM_INDGRP)

class LED_PWM_Channel:
    LED_0  = const(0x02)  # LED D1 BLUE
    LED_1  = const(0x03)  # LED D1 GREEN
    LED_2  = const(0x04)  # LED D1 RED
    LED_3  = const(0x05)  # LED D1 Not Connected
    GRPPWM = const(0x06)  # Group Duty Cycle Control Register

    _All = (LED_0, LED_1, LED_2, LED_3, GRPPWM)

class LED_Auto_incr:
    """Auto-increment options when writing multiple bytes from a start register."""
    NONE      = const(0b000)  # No increment.
    ALL       = const(0b100)  # Increment on every register write.
    IND       = const(0b101)  # Increment individual regs only (eg brightness/PWM channel)
    GLOBAL    = const(0b110)  # Increment global control regs only
    INDGLOBAL = const(0b111)  # Increment both individual and global regs

    _All = (NONE, ALL, IND, GLOBAL, INDGLOBAL)


# Register pointers
REG_MODE1 = const(0x00)

class LED_REG_Mode1:
    def __init__(self, allcal=0, s3=0, s2=0, s1=0, osc=0, incr=0):
        super().__init__()
        self.ALLCAL   = allcal  # : 1   Device responds to ALLCALL address
        self.SUB3     = s3      # : 1   Device responds to sub address 3
        self.SUB2     = s2      # : 1   Device responds to sub address 2
        self.SUB1     = s1      # : 1   Device responds to sub address 1
        self.OSC      = osc     # : 1   Oscillator on (0: default) or off (1)
        self.AUTOINCR = incr    # : 3   Auto-increment options

    def byte(self):
        bits = bit(5, self.AUTOINCR, 3) \
             | bit(4, self.OSC)         \
             | bit(3, self.SUB1)        \
             | bit(2, self.SUB2)        \
             | bit(1, self.SUB3)        \
             | bit(0, self.ALLCAL)
        return bytes([bits])

    @classmethod
    def from_bytes(cls, raw):
        raw = to_single_byte(raw)
        return cls(get(raw, 0),
                   get(raw, 1), get(raw, 2), get(raw, 3),
                   get(raw, 4), get(raw, 5, 3))


REG_MODE2 = const(0x01)

class LED_REG_Mode2:
    def __init__(self, outdrv=1, och=0, invrt=0, dmblnk=0):
        super().__init__()
        self.OUTNE      = 0b01      # : 2     Not used for this version (01: default)
        self.OUTDRV     = outdrv    # : 1     The 4 LED outputs are configured with a totem pole structure (1: default), or open-drain structure (0)
        self.OCH        = och       # : 1     Output changes on stop command (0: default) or on ACK (1)
        self.INVRT      = invrt     # : 1     Output logic state not inverted (0: default), when no external driver is used
                                    #         Output logic state inverted (1), when external driver is used
        self.DMBLNK     = dmblnk    # : 1     Group control dimming (0: default) or blinking (1)
        self.UNUSED_02  = 0b00      # : 2     Keep at 0

    def byte(self):
        bits = bit(6, self.UNUSED_02, 2) \
             | bit(5, self.DMBLNK)       \
             | bit(4, self.INVRT)        \
             | bit(3, self.OCH)          \
             | bit(2, self.OUTDRV)       \
             | bit(0, self.OUTNE, 2)
        return bytes([bits])

    @classmethod
    def from_bytes(cls, raw):
        raw = to_single_byte(raw)
        return cls(get(raw, 2), get(raw, 3), get(raw, 4), get(raw, 5))


REG_LED_START = const(0x02) # PWM values for rgba for each led [0, 3] in 0x02-0x05
REG_GRPPWM    = const(0x06) # Group dutycycle control (if mode2.DMBLNK == 0)
REG_GRPFREQ   = const(0x07) # Group frequency control (period)  (if mode2.DMBLNK == 1)


REG_LEDOUT = const(0x08)   # LED output state with LED_Mode for each LED

class LED_REG_Out_state:
    def __init__(self, l0=0, l1=0, l2=0, l3=0):
        super().__init__()
        self.LED0 = l0
        self.LED1 = l1
        self.LED2 = l2
        self.LED3 = l3

    def byte(self):
        bits = bit(6, self.LED3, 2) \
             | bit(4, self.LED2, 2) \
             | bit(2, self.LED1, 2) \
             | bit(0, self.LED0, 2)
        return bytes([bits])

    @classmethod
    def from_bytes(cls, raw):
        raw = to_single_byte(raw)
        return cls(get(raw, 0, 2), get(raw, 2, 2), get(raw, 4, 2), get(raw, 6, 2))


REG_SUBADR1 = const(0x09)   # I2C bus subaddr 1
REG_SUBADR2 = const(0x0a)   # I2C bus subaddr 2
REG_SUBADR3 = const(0x0b)   # I2C bus subaddr 3
REG_ALLCALL = const(0x0c)   # LED All cal I2C addr


class LEDColour:
    def __init__(self, r=0, g=0, b=0, a=0):
        super().__init__()
        self.red   = r
        self.green = g
        self.blue  = b
        self.amber = g

    def byte(self):
        # BLUE, GREEN, RED, AMBER
        return bytes((self.blue, self.green, self.red, self.amber))

    @classmethod
    def from_hex(cls, hex_val):
        hex_val = int(hex_val, 16) or 0
        red     = (hex_val & 0xFF000000) >> 24
        green   = (hex_val & 0x00FF0000) >> 16
        blue    = (hex_val & 0x0000FF00) >> 8
        amber   = (hex_val & 0x000000FF)
        return cls(red, green, blue, amber)


class LEDColourDefault:
    BLACK   = LEDColour(0x00, 0x00, 0x00)
    RED     = LEDColour(0xFF, 0x00, 0x00)
    GREEN   = LEDColour(0x00, 0xFF, 0x00)
    BLUE    = LEDColour(0x00, 0x00, 0xFF)
    ORANGE  = LEDColour(0xD0, 0x70, 0x00)
    YELLOW  = LEDColour(0xC8, 0xFF, 0x00)
    CYAN    = LEDColour(0x00, 0xFF, 0xFF)
    MAGENTA = LEDColour(0xFF, 0x00, 0xFF)
    WHITE   = LEDColour(0xCB, 0xFF, 0xF0)
    TEST    = LEDColour(0xCB, 0xFF, 0xF0)

    _LUT = {
        0 : BLACK    ,
        1 : RED    ,
        2 : GREEN  ,
        3 : BLUE   ,
        4 : ORANGE ,
        5 : YELLOW ,
        6 : CYAN   ,
        7 : MAGENTA,
        8 : WHITE  ,
    }

    @staticmethod
    def get(idx):
        return LEDColourDefault._LUT.get(idx % len(LEDColourDefault._LUT), LEDColourDefault.BLACK)


class PCA9632():
    def __init__(self, i2c=None, addr=ADDR_BASE):
        super().__init__()
        if i2c == None or i2c.__class__ != I2C:
            raise ValueError('I2C object needed as argument!')
        self._i2c  = i2c
        self._addr = addr
        self._check_device()

    def _send_raw(self, addr, buf):
        """
        Sends the given buffer object over I2C to the address.
        """
        if hasattr(self._i2c, "writeto"):
            # Micropython
            self._i2c.writeto(addr, buf)
        elif hasattr(self._i2c, "send"):
            # PyBoard Micropython
            self._i2c.send(addr, buf)
        else:
            raise Exception("Invalid I2C object. Unknown Micropython/platform?")

    def _send(self, buf):
        self._i2c._send_raw(self._addr, buf)

    def _recv(self, n):
        """
        Read bytes from the sensor using I2C. The byte count must be specified
        as an argument.
        Returns a bytearray containing the result.
        """
        if hasattr(self._i2c, "writeto"):
            # Micropython (PyCom)
            return self._i2c.readfrom(self._addr, n)
        elif hasattr(self._i2c, "send"):
            # PyBoard Micropython
            return self._i2c.recv(n, self._addr)
        else:
            raise Exception("Invalid I2C object. Unknown Micropython/platform?")

    def _writemem(self, memaddr, data):
        self._i2c.writeto_mem(self._addr, memaddr, data)

    def _readmem(self, memaddr, size):
        return self._i2c.readfrom_mem(self._addr, memaddr, size)

    def _check_device(self):
        pass

    def config(self, sub1=0, sub2=0, sub3=0, allcal=0, osc=0, dimming=True, blinking=False):
        if any((allcal, sub3, sub2, sub1, osc)):
            reg = LED_REG_Mode1(allcal, sub3, sub2, sub1, osc)
            self._send(bytes([REG_MODE1]) + reg.byte())

        if any((dimming, blinking)):
            # OCH   : Output on stop command => sync
            # DMBLNK: Group control dimming (0: default) or blinking (1)

            reg = LED_REG_Mode2(och=0)
            if blinking:
                reg.DMBLNK = 1
            elif dimming and not blinking:
                reg.DMBLNK = 0

            self._send(bytes([REG_MODE2]) + reg.byte())

        self.set_output_mode_all(LED_Mode.PWM_INDGRP)
        self.set_colour_all(LEDColourDefault.BLACK)

    def set_brightness(self, pwm_channel, dutycycle):
        if pwm_channel not in LED_PWM_Channel._All:
            raise Exception("set_brightness: Invalid pwm_channel?")
        self._send(bytes((pwm_channel, dutycycle & 0xFF)))

    def set_brightness_all(self, dutycycle):
        self._send(bytes((LED_PWM_Channel.GRPPWM, dutycycle & 0xFF)))

    def set_colour_all(self, colour):
        if not isinstance(colour, LEDColour):
            raise Exception("set_colour_all: Invalid colour?")
        addr = int(LED_REG_Mode1(incr=LED_Auto_incr.IND).byte()[0]) | LED_PWM_Channel.LED_0
        self._send(bytes([addr]) + colour.byte())

    def set_output_mode(self, pwm_channel, mode):
        """Only change given channel by reading previous register value."""
        if pwm_channel not in LED_PWM_Channel._All:
            raise Exception("set_output_mode: Invalid pwm_channel?")
        if mode not in LED_Mode._All:
            raise Exception("set_output_mode: Invalid mode?")

        prev_state = self._readmem(REG_LEDOUT, 1)  # Or self._send(bytes([REG_LEDOUT])); self._recv(1) ??
        reg        = LED_REG_Out_state.from_bytes(prev_state)

        if pwm_channel == LED_PWM_Channel.LED_0:
            reg.LED0 = mode
        elif pwm_channel == LED_PWM_Channel.LED_1:
            reg.LED1 = mode
        elif pwm_channel == LED_PWM_Channel.LED_2:
            reg.LED2 = mode
        elif pwm_channel == LED_PWM_Channel.LED_3:
            reg.LED3 = mode

        self._send(bytes([REG_LEDOUT]) + reg.byte())

    def set_output_mode_all(self, mode):
        if mode not in LED_Mode._All:
            raise Exception("set_output_mode_all: Invalid mode?")
        addr = int(LED_REG_Mode1(incr=LED_Auto_incr.IND).byte()[0]) | REG_LEDOUT
        reg  = LED_REG_Out_state(mode, mode, mode, mode)

        self._send(bytes([addr]) + reg.byte())

    def set_blink_freq(self, dutycycle):
        self._send(bytes((REG_GRPFREQ, dutycycle & 0xFF)))
