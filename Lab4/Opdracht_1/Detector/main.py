from screentracker import ScreenTracker
from bits import Bits
from colours import *

import numpy as np
from bitarray import bitarray


class Detector:
    def __init__(self, true_ratio=0.5, start_bits=bitarray("110011"), stop_bytes=b"\n"):
        super().__init__()

        self.true_ratio = true_ratio or 0.5
        self.start_bits = start_bits if isinstance(start_bits, bitarray) else bitarray(start_bits)
        self.stop_bytes = stop_bytes or b"\n"
        self.data       = bitarray()
        self.buffer     = bitarray()

        self.received  = [b""]
        self.got_start = False

        self.value_size  = 2  # Least amount of values in window that need to be the same
        self.window_size = 2  # Amount of values to process before determining one bit

    def _log(self, msg):
        print(style("[Detector]", Colours.FG.YELLOW), msg)

    def reset(self):
        self.data   = bitarray()
        self.buffer = bitarray()
        self.received = [b""]
        self.got_start = False

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
        length, start_length = self.buffer.length(), self.start_bits.length()

        if not self.got_start:
            if length >= start_length:
                try:
                    self._log(self.buffer.to01())
                    idx = self.buffer.to01().index(self.start_bits.to01())
                except ValueError:
                    self.got_start = False
                else:
                    self._log(f"Got start bits, receiving until {self.stop_bytes}...")
                    self.buffer    = self.buffer[idx + start_length:]
                    length         = self.buffer.length()
                    self.got_start = True

        if self.got_start:
            while length >= self.window_size:
                # Slice window out of buffer
                window, self.buffer = self.buffer[0:self.window_size], self.buffer[self.window_size:]
                length = self.buffer.length()

                # Count amount of True/False bits in window
                positive = window.count(True)
                # negative = self.window_size - positive

                # On self.window_size received 0/1 bits, append 0/1 bit to data
                self.data.append(positive >= self.value_size)

                if self.data.length() % 8 == 0:
                    # Got at least 1 full byte
                    bytestr = self.data.tobytes()
                    self.received[-1] = bytestr

                    self._log(f"Got: {self.data[-8:].to01()} => ({len(bytestr)}) {bytestr}")

                    if bytestr.endswith(self.stop_bytes):
                        # Remove stop bytes
                        bytestr = bytestr[0:-len(self.stop_bytes)]
                        bytestr = str(Bits.bytes_to_str(bytestr))
                        self.received[-1] = bytestr

                        self._log(f"Completed: {bytestr}")
                        self._log("Reset...")
                        self.data = bitarray()
                        self.received.append(b"")
                        self.got_start = False

        return (f"Data: {int(ratio * 100)}% white, Found start bits? {self.got_start}",) + tuple(map(str, self.received))


if __name__ == "__main__":
    d = Detector(start_bits="111100001111")
    tracker = ScreenTracker(input_callback=d.determine_bits, reset_callback=d.reset, tracker="mil", fps_limit=8)
    tracker.start()
