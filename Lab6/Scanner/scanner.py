from access_points import get_scanner
import traceback
import math
import time

from colours import Colours, style
from threads import Threading
from positioning import Position, Point


class Locations:
    _LUT = {
        "4c:ed:fb:a6:00:bc" : Point(  1.01, 5.01),  # Vibenet_5G (boven)
        "4c:ed:fb:a6:00:b8" : Point(  1.00, 5.00),  # Vibenet (boven)
        "60:45:cb:59:f0:51" : Point(  0.00, 0.00),  # Vibenet (onder)     ~ 9m
        "60:45:cb:59:f0:54" : Point(  0.01, 0.01),  # Vibenet_5G (onder)
        "c8:d1:2a:89:c5:80" : Point(-20.00, 8.00),  # telenet-6736672

        "50:C7:BF:FE:39:A7" : Point(0, 0),  # Eskettiiit
        "00:14:5C:8C:EE:98" : Point(0, 0),  # ItHurtsWhenIP
        "C0:25:E9:E0:EE:6E" : Point(0, 0),  # G-Spot
        "76:A8:FB:BF:90:BD" : Point(0, 0),  # BramSpot
    }

    _NOT_GROUND_LEVEL = (
        "4c:ed:fb:a6:00:bc", "4c:ed:fb:a6:00:b8",
        "50:C7:BF:FE:39:A7", "C0:25:E9:E0:EE:6E"
    )

    @staticmethod
    def get_point(mac, ground_only=False):
        return Locations._LUT.get(mac, None) \
            if not ground_only or (ground_only and mac not in Locations._NOT_GROUND_LEVEL) else None


class Scanner:
    def __init__(self):
        super().__init__()
        self.scanner = get_scanner()
        self.scanner_lock = Threading.new_lock()

        self.sampling_thread = None
        self.sampling_thread_running = True

        self.access_points = {}
        self.access_points_lock = Threading.new_lock()

        self.current_location = Point(0, 0)

    ###########################################################################

    def __del__(self):
        if self.sampling_thread:
            self.sampling_thread_running = False
            self.sampling_thread.join()

    def __str__(self):
        with self.access_points_lock:
            if self.access_points:
                printed = "\n".join("{0:<30} {1}: {2}%".format(
                        style(ssid , Colours.FG.BRIGHT_YELLOW),
                        style(f"({bssid})", Colours.FG.BRIGHT_BLACK),
                        v
                    ) for (ssid, bssid), v in sorted(self.access_points.items(), key=lambda x: x[1]))
            else:
                printed = style("No APs sampled! Run sample command first.", Colours.FG.BRIGHT_RED)

        return style("Scanner Access Points:", Colours.FG.YELLOW) + "\n" + printed

    def _log(self, msg):
        print(style(f"[Scanner]", Colours.FG.YELLOW), msg)

    def _err(self, e=None, prefix=""):
        if e:
            self._log(prefix + style(type(e).__name__, Colours.FG.RED) + f": {e}")
            self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
        else:
            self._log(prefix + style("Unknown error", Colours.FG.RED))

    ###########################################################################

    def sample(self, log=True):
        # Calls on windows: `netsh wlan show networks mode=bssid`
        with self.scanner_lock:
            aps = self.scanner.get_access_points()

        if not aps and log:
            self._log(style(f"No Access Points in range or no WLAN interface available (with {self.scanner})!", Colours.FG.BRIGHT_RED))
            return

        if log:
            self._log(f"Updated info for {len(aps)} access points.")
        with self.access_points_lock:
            self.access_points.update(self.aps_to_dict(aps))

    @staticmethod
    def aps_to_dict(aps):
        return { (ap['ssid'], ap['bssid']) : ap['quality'] for ap in aps}

    def get_ap_distance(self, signal_strength_dbm, strategy=2, signal_frequency=2.4, signal_attentuation=3, signal_strength_ref=-50, signal_dist_ref=4):
        if strategy == 1:
            return self._calc_signal_distance_simple(signal_strength_dbm,
                                                     signal_frequency=signal_frequency)
        elif strategy == 2:
            return self._calc_signal_distance(signal_strength_dbm,
                                              signal_attentuation = signal_attentuation,
                                              signal_strength_ref = signal_strength_ref,
                                              signal_dist_ref     = signal_dist_ref)
        self._log(style("Unknown strategy?", Colours.FG.BRIGHT_RED))
        return -1

    ###########################################################################

    def _sample_thread(self, interval_s=1):
        self._log(f"Start sampling thread ({interval_s}s delay)...")

        while self.sampling_thread_running:
            self._handle_sample(log=False)
            time.sleep(interval_s)

    def start_interactive(self):
        self.sampling_thread = Threading.new_thread(self._sample_thread, (1,))

        print(style("Command list:", Colours.FG.BLACK, Colours.BG.YELLOW) + " " + ", ".join(Commands.CHOICES))

        while True:
            print(style("Enter command: ", Colours.FG.BLACK, Colours.BG.YELLOW))
            raw = input()
            Commands.handle_cmd(raw, self)

    ###########################################################################

    @staticmethod
    def _calc_signal_distance_simple(signal_strength_dbm, signal_frequency=2.4):
        exp = (27.55 - (20 * math.log10(signal_frequency * 1000)) + abs(signal_strength_dbm)) / 20.0
        return round(10 ** exp, 4)

    @staticmethod
    def _calc_signal_distance(signal_strength_dbm, signal_attentuation=3, signal_strength_ref=-50, signal_dist_ref=4):
        beta_numerator   = float(signal_strength_ref - signal_strength_dbm)
        beta_denominator = float(10 * signal_attentuation)
        beta = beta_numerator / beta_denominator
        return round((10**beta) * signal_dist_ref, 4)

    def _handle_print(self):
        print(self)

    def _handle_sample(self, log=True):
        try:
            self.sample(log)
        except Exception as e:
            self._err(e, "Sampling ")

    def _handle_position(self):
        positions = []

        with self.access_points_lock:
            for (ssid, bssid), quality in self.access_points.items():
                point = Locations.get_point(bssid, ground_only=False)

                if point:
                    radius = quality  # TODO convert % to dBm
                    positions.append(Position(point, radius))

        if len(positions) > 2:
            positions = list(sorted(positions, key=lambda x: x.radius, reverse=True))
            p1, p2, p3 = positions[0], positions[1], positions[2]

            self.current_location = p1.intersection(p2, p3)

            print(style("Updated position: ", Colours.FG.GREEN) \
                + style(f"{self.current_location}", Colours.FG.BRIGHT_GREEN))

    def _handle_clear(self):
        with self.access_points_lock:
            self.access_points = {}
            self.lowest_quality, self.highest_quality = "", ""

    def _handle_exit(self):
        exit(0)


class Commands:
    PRINT_CURRENT = "print"
    SAMPLE        = "sample"
    POSITION      = "position"
    CLEAR         = "clear"
    EXIT          = "exit"

    CHOICES = ( PRINT_CURRENT, SAMPLE, POSITION, CLEAR, EXIT )

    @staticmethod
    def handle_cmd(cmd, scanner):
        cmd = cmd.lower().strip()

        if not cmd:
            return
        if not cmd in Commands.CHOICES:
            print(style(f"Invalid command '{cmd}'?", Colours.FG.RED))
            return

        handler = {
            Commands.PRINT_CURRENT : scanner._handle_print,
            Commands.SAMPLE        : scanner._handle_sample,
            Commands.POSITION      : scanner._handle_position,
            Commands.CLEAR         : scanner._handle_clear,
            Commands.EXIT          : scanner._handle_exit,
        }

        handler.get(cmd)()


if __name__ == "__main__":
    """
    Considerations:
        - Add live plot mapping RSSI for all APs that were detected at one point?
        - 2D representation of AP locations (unknown?) and RSSI as circles
            -> intersection with _calc_intersetion() represents device location
        - Something like: https://github.com/kootenpv/whereami
    """

    wifi_scanner = Scanner()
    wifi_scanner.start_interactive()
