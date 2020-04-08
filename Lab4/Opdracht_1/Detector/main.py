from screentracker import ScreenTracker
from bits import Bits
from colours import *

import numpy as np
from bitarray import bitarray


class Detector:
    def __init__(self, true_ratio=0.5):
        super().__init__()

        self.true_ratio = true_ratio
        self.data       = bitarray()
        self.buffer     = bitarray()

        self.received = []

        self.value_size  = 2  # Least amount of values in window that need to be the same
        self.window_size = 2  # Amount of values to process before determining one bit

    def _log(self, msg):
        print(style("[Detector]", Colours.FG.YELLOW), msg)

    def determine_bits(self, frame):
        # Callback gets called 16 times per second (16 fps limit)
        # Acquisition rate should be twice the input,
        # thus check the frame twice and if both have the same result,
        # use that value.
        # Max transmission rate is 8 bits per second, or 1 byte/char per second.

        # whites = np.where(frame >= 128)
        whites = (frame >= 128).sum()
        ratio  = whites / frame.size

        self.buffer.append(ratio >= self.true_ratio)
        length = self.buffer.length()

        if length == self.window_size:
            positive = self.buffer.count(True)
            negative = length - positive

            # On self.window_size received 0/1 bits, append 0/1 bit to data
            if positive >= self.value_size:
                self.data.append(True)
            elif negative >= self.value_size:
                self.data.append(False)

            self.buffer = bitarray()

        return ("Data: {0}% white".format(int(ratio * 100),)) +  tuple(self.received)

        # return Bits.bytes_to_str(self.data)


if __name__ == "__main__":
    d = Detector()
    tracker = ScreenTracker(input_callback=d.determine_bits, tracker="csrt", fps_limit=16)
    tracker.start()
