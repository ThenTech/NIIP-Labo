from screentracker import ScreenTracker, HandlerData
from bits import Bits
from colours import *

import numpy as np
import cv2
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

        self.prev_clk = False

        self.value_size  = 2  # Least amount of values in window that need to be True to count as '1'
        self.window_size = 2  # Amount of values to process before determining one bit
        self.capturing_window = False

        self.ct, self.dt = bitarray(), bitarray()


    def _log(self, msg):
        print(style("[Detector]", Colours.FG.YELLOW), msg)

    def reset(self):
        self.data   = bitarray()
        self.buffer = bitarray()
        self.received = [b""]
        self.got_start = False

    def determine_bits(self, frame):
        ret = HandlerData()

        # Orient to portrait
        h, w = frame.shape

        if w > h:
            # Turn 90°
            frame = np.rot90(frame, axes=(1,0))
            h, w = w, h

        # Divide frame in top (clock) and bottom (data)
        half = h // 2

        frame_clock = frame[0:half, 0:w]
        frame_data  = frame[half:half*2, 0:w]

        ret.add_screen("Clock", frame_clock)
        ret.add_screen("Data", frame_data)

        clk, data = (frame_clock >= 128).sum(), (frame_data >= 128).sum()
        clk, data = clk / frame_clock.size, data / frame_data.size
        clk, data = clk >= self.true_ratio, data >= self.true_ratio

        # self.ct.append(clk)
        # self.dt.append(data)
        # print(f"c: {self.ct.to01()}\nd: {self.dt.to01()}")


        if self.prev_clk != clk:
            self.prev_clk = clk
            self.capturing_window = True

            ret.add_info(f"clk={clk}, data={data}, Found start bits? {self.got_start}")
            for d in self.received:
                ret.add_info(str(d))
            return ret

        if self.capturing_window:
            self.data.append(data)
        self.capturing_window = False

        if not self.got_start:
            start_length = self.start_bits.length()

            if self.data.length() >= start_length:
                try:
                    self._log(self.data.to01())
                    idx = self.data.to01().index(self.start_bits.to01())
                except ValueError:
                    self.got_start = False
                else:
                    self._log(f"Got start bits, receiving until {self.stop_bytes}...")
                    self.data      = self.data[idx + start_length:]
                    self.got_start = True

        elif self.got_start:
            if self.data.length() > 0 and self.data.length() % 8 == 0:
                # Got at least 1 full byte
                bytestr = self.data.tobytes()

                if len(self.received[-1]) != len(bytestr):
                    self._log(f"Got: {self.data[-8:].to01()} => ({len(bytestr)}) {bytestr}")

                self.received[-1] = bytestr

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


        ret.add_info(f"clk={clk}, data={data}, Found start bits? {self.got_start}")
        for d in self.received:
            ret.add_info(str(d))

        return ret







        if self.capturing_window:
            self.buffer.append(data)

            if self.buffer.length() >= self.window_size:
                self.capturing_window = False

                window, self.buffer = self.buffer[0:self.window_size], self.buffer[self.window_size:]
                self.buffer = bitarray()

                # Count amount of True/False bits in window
                positive = window.count(True)
                print(f"{window.to01()} => data + {positive >= self.value_size}")

                # On self.window_size received 0/1 bits, append 0/1 bit to data
                self.data.append(positive >= self.value_size)

                if not self.got_start:
                    start_length = self.start_bits.length()

                    if self.data.length() >= start_length:
                        try:
                            self._log(self.data.to01())
                            idx = self.data.to01().index(self.start_bits.to01())
                        except ValueError:
                            self.got_start = False
                        else:
                            self._log(f"Got start bits, receiving until {self.stop_bytes}...")
                            self.data      = self.data[idx + start_length:]
                            self.got_start = True

                elif self.data.length() % 8 == 0:
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

        if self.prev_clk != clk:
            # On clk change, start window capture
            print(f"Change clk {self.prev_clk} -> {clk} :: {data} data")
            self.prev_clk = clk
            self.capturing_window = True
            # self.buffer.append(data)

        ret.add_info(f"clk={clk}, data={data}, Found start bits? {self.got_start}")
        for d in self.received:
            ret.add_info(str(d))

        return ret


        ## Method 2

        # Determine data value
        if self.prev_clk != clk:
            print(f"Change clk {self.prev_clk} -> {clk} :: {data} data")
            self.prev_clk = clk
            self.buffer.append(data)

            self.capturing_window = True

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
                    window, self.buffer = self.buffer[1:self.window_size], self.buffer[self.window_size:]
                    length = self.buffer.length()

                    # Count amount of True/False bits in window
                    positive = window.count(True)

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
        elif self.capturing_window:
            # Same clock but still in window capture
            self.buffer.append(data)
            if self.buffer.length() >= self.window_size:
                self.capturing_window = False

        ret.add_info(f"clk={clk}, data={data}, Found start bits? {self.got_start}")
        for d in self.received:
            ret.add_info(str(d))

        return ret

        ##### OLD METHOD

        # Callback gets called 16 times per second (16 fps limit)
        # Acquisition rate should be twice the input,s
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
    d = Detector(start_bits="11110011")
    tracker = ScreenTracker(input_callback=d.determine_bits, reset_callback=d.reset, tracker="mil", fps_limit=60)
    tracker.start()
