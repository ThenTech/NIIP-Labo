from access_points_enhanced import get_scanner
import traceback
import math
import time
import matplotlib.pyplot as plt
import sys

from colours import Colours, style
from threads import Threading
from positioning import Position, Point, Quality
from sniffer import Sniffer


class Locations:
    _LUT = {
        "4C:ED:FB:A6:00:BC" : Point(  0.01, -3.01),  # Vibenet_5G (boven)
        "4C:ED:FB:A6:00:B8" : Point(  0.00, -3.00),  # Vibenet (boven)
        "60:45:CB:59:F0:51" : Point(  0.00,  0.00),  # Vibenet (onder)     ~ 9m
        "60:45:CB:59:F0:54" : Point(  0.01,  0.01),  # Vibenet_5G (onder)
        "C8:D1:2A:89:C5:80" : Point(-20.00, -8.00),  # telenet-6736672
        "96:5E:E3:AF:4D:81" : Point(  5.00, -2.00),  # Synchrotron
        "16:30:A9:A5:2C:F9" : Point(  5.00, -2.00),  # Synchrotron

        # "50:C7:BF:FE:39:A7" : Point(  0.00,  0.00),  # Eskettiiit
        "00:14:5C:8C:EE:98" : Point(  3.70,  1.20),  # ItHurtsWhenIP
        "C0:25:E9:E0:EE:6E" : Point(  0.00,  9.00),  # G-Spot
        "18:81:0E:87:E1:82" : Point(  0.00,  9.00),  # G-Spot
        "76:A8:FB:BF:90:BD" : Point(  1.80,  3.30),  # BramSpot
        "BE:86:B9:99:ED:D3" : Point(  1.80,  3.30),  # BramSpot
    }

    _NOT_GROUND_LEVEL = (
        "4C:ED:FB:A6:00:BC", "4C:ED:FB:A6:00:B8",
        "50:C7:BF:FE:39:A7", "C0:25:E9:E0:EE:6E"
    )

    @staticmethod
    def get_point(mac, ground_only=False):
        mac = mac.upper()
        return Locations._LUT.get(mac, None) \
            if not ground_only or (ground_only and mac not in Locations._NOT_GROUND_LEVEL) else None


class Scanner:
    class Mode:
        BASIC        = 0
        BASIC_IWLIST = 1
        SNIFFING     = 2

    class PositioningMode:
        TRILATERATION    = 0
        TRILAT_ESTIM     = 1
        TRILAT_ESTIM_ALL = 2

    def __init__(self, mode=Mode.BASIC, interface="wlp2s0", force_iwlist=False, bg_img=""):
        super().__init__()
        self.scanner = None

        if mode in (Scanner.Mode.BASIC, Scanner.Mode.BASIC_IWLIST):
            force_iwlist = force_iwlist or mode == Scanner.Mode.BASIC_IWLIST
            self.scanner = get_scanner(interface, force_iwlist)

            if force_iwlist:
                # IWList needs sudo, so call to enter password first time
                self.scanner.get_access_points()
        elif mode in (Scanner.Mode.SNIFFING,):
            self.scanner = Sniffer(interface=interface)
            self.scanner.start()

        self.scanner_lock = Threading.new_lock()

        self.sampling_thread = None
        self.sampling_thread_running = True

        self.access_points = {}
        self.access_points_lock = Threading.new_lock()

        self.last_mode = Scanner.PositioningMode.TRILATERATION
        self.current_aps = tuple()
        self.current_location = Point(0, 0)

        self.bg_img = None
        self.bg_loc = None

        if bg_img:
            try:
                fname, params     = bg_img.split(';', 1)
                xloc, yloc, scale = map(float, params.split(';'))

                self.bg_img = plt.imread(fname, format='png')

                size_y, size_x = self.bg_img.shape[1], self.bg_img.shape[0]
                left_bottom    = Point(-float(xloc) / scale, -float(yloc) / scale)
                right_top      = Point(left_bottom.x + size_x / scale, left_bottom.y + size_y / scale)
                self.bg_loc    = (left_bottom, right_top)
            except Exception as e:
                self._log(style(f"Could not parse background image: {bg_img}\n{e}", Colours.FG.RED))

    ###########################################################################

    def _kill_threads(self):
        if self.sampling_thread:
            self.sampling_thread_running = False
            self.sampling_thread.join()

    def __del__(self):
        self._kill_threads()

    def __str__(self):
        with self.access_points_lock:
            if self.access_points:
                printed = "\n".join("{0:<30} {1}: {2}{3}".format(
                        style(ssid , Colours.FG.BRIGHT_YELLOW),
                        style(f"({bssid})", Colours.FG.BRIGHT_BLACK),
                        round(v.get(), 2),
                        "%" if v.is_percentage() else "dBm"
                    ) for (ssid, bssid), v in sorted(self.access_points.items(), key=lambda x: x[1].get()))
            else:
                printed = style("No APs sampled! Run sample command first.", Colours.FG.BRIGHT_RED)

        return style("Scanner Access Points:", Colours.FG.MAGENTA) + "\n" + printed

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
            for (ssid, bssid), rssi in self.aps_to_dict(aps).items():
                if (ssid, bssid) in self.access_points:
                    self.access_points[(ssid, bssid)].update(rssi)
                else:
                    self.access_points[(ssid, bssid)] = Quality(value=rssi, tag=Quality.TAG_DBM)

    @staticmethod
    def aps_to_dict(aps):
        return { (ap['ssid'], ap['bssid']) : ap['quality'] for ap in aps}

    def get_ap_distance(self, signal_strength_dbm, strategy=2, signal_frequency=2.4, signal_attentuation=3, signal_strength_ref=-58, signal_dist_ref=2):
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

        time.sleep(0.2)
        print(style("Command list:", Colours.FG.BLACK, Colours.BG.YELLOW) + " " + ", ".join(Commands.CHOICES))

        while True:
            try:
                print(style("Enter command:", Colours.FG.BLACK, Colours.BG.YELLOW), end=" ")
                raw = input()
                Commands.handle_cmd(raw, self)
            except KeyboardInterrupt:
                self._handle_exit()

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

    def _handle_position(self, mode=PositioningMode.TRILATERATION):
        self.last_mode     = mode
        positions_filtered = []

        with self.access_points_lock:
            for (ssid, bssid), quality in self.access_points.items():
                point = Locations.get_point(bssid, ground_only=False)
                is_5g = "5G" in ssid.upper()

                if point and not is_5g:
                    radius = self.get_ap_distance(quality.get(),
                                                  signal_frequency=5.0 if is_5g else 2.4,
                                                  signal_attentuation=5.0,
                                                  signal_strength_ref=-38, signal_dist_ref=3)
                    positions_filtered.append(Position((ssid, bssid), point, radius))
                # elif not point:
                #     print(style(f"Unknown AP {ssid} ({bssid}), please add it to the list?", Colours.FG.BRIGHT_RED))

        if len(positions_filtered) > 1:
            pos_sorted = list(sorted(positions_filtered, key=lambda x: x.radius, reverse=False))

            if len(positions_filtered) > 2:
                # If we found at least 3 APs
                p1, p2, p3 = pos_sorted[0], pos_sorted[1], pos_sorted[2]

                self.current_aps = (p1, p2, p3)
                if mode == Scanner.PositioningMode.TRILATERATION:
                    self.current_location = p1.intersection(p2, p3)
                elif mode == Scanner.PositioningMode.TRILAT_ESTIM:
                    self.current_location = p1.intersection_estimate(p2, p3, get_all=False)
                elif mode == Scanner.PositioningMode.TRILAT_ESTIM_ALL:
                    self.current_location = p1.intersection_estimate(p2, p3, get_all=True)
            else:
                p1, p2 = pos_sorted[0], pos_sorted[1]
                self.current_aps = (p1, p2)
                self.current_location = p1.intersection_estimate_other(p2)

            if isinstance(self.current_location, Point):
                self.current_location = (self.current_location,)

            print(style("Estimated AP distances:", Colours.FG.MAGENTA))
            print("\n".join("{0:<30} {1} @ {2}: {3}m".format(
                    style(p.name[0] , Colours.FG.BRIGHT_YELLOW),
                    style(f"({p.name[1]})", Colours.FG.BRIGHT_BLACK),
                    p.location,
                    f"{round(p.radius, 2):.2f}"
                ) for p in self.current_aps))

            print(style("Updated device position: ", Colours.FG.GREEN) \
                + style(f"{', '.join(map(str, self.current_location))}", Colours.FG.BRIGHT_GREEN))
        else:
            print(style(f"Not enough APs in range to get position? ({len(positions_filtered)}:{positions_filtered})", Colours.FG.BRIGHT_RED))

    def _handle_plot(self):
        self._handle_position(self.last_mode)

        plt.axis([-400, 400, -400, 400])
        plt.xlabel('X axis (m)')
        plt.ylabel('Y axis (m)')
        ax = plt.gca()

        for p in self.current_aps:
            plt.plot(p.location.x, p.location.y,'ro')
            ax.add_artist(plt.Circle((p.location.x, p.location.y), p.radius, color='r', fill=False, clip_on=True))
            plt.annotate(f"{p.name[0]}\n{round(p.radius, 2)} m",
                         xy=(p.location.x, p.location.y),
                         xycoords='data',
                         xytext=(-30, +40),
                         textcoords='offset points',
                         fontsize=10,
                         arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

        single = len(self.current_location) == 1

        for p in self.current_location:
            plt.plot(p.x, p.y, 'bo')
            plt.annotate(f"Device\n{p}" if single else "",
                        xy=(p.x, p.y),
                        xycoords='data',
                        xytext=(0, -30),
                        textcoords='offset points',
                        fontsize=10,
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2") if single else \
                                   None)

        if self.bg_img is not None:
            # (left, right, bottom, top)
            plt.imshow(self.bg_img, zorder=0, extent=(self.bg_loc[0].x, self.bg_loc[1].x, self.bg_loc[0].y, self.bg_loc[1].y))

        plt.xlim(-25, 25)
        plt.ylim(-25, 25)
        ax.set_aspect('equal', adjustable='box')
        plt.show()

    def _handle_clear(self):
        with self.access_points_lock:
            self.access_points = {}
            self.lowest_quality, self.highest_quality = "", ""

    def _handle_exit(self):
        self._kill_threads()
        exit(0)


class Commands:
    PRINT_CURRENT = "print"
    SAMPLE        = "sample"
    POSITION      = "position"
    POSITION_EST  = "positionest"
    POSITION_ALL  = "positionall"
    PLOT          = "plot"
    CLEAR         = "clear"
    EXIT          = "exit"

    CHOICES = ( PRINT_CURRENT, SAMPLE, POSITION, POSITION_EST, POSITION_ALL, PLOT, CLEAR, EXIT )

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
            Commands.POSITION_EST  : scanner._handle_position,
            Commands.POSITION_ALL  : scanner._handle_position,
            Commands.PLOT          : scanner._handle_plot,
            Commands.CLEAR         : scanner._handle_clear,
            Commands.EXIT          : scanner._handle_exit,
        }

        if cmd in (Commands.POSITION_EST, Commands.POSITION_ALL):
            handler.get(cmd)(Scanner.PositioningMode.TRILAT_ESTIM if cmd == Commands.POSITION_EST else \
                             Scanner.PositioningMode.TRILAT_ESTIM_ALL)
        else:
            handler.get(cmd)()


if __name__ == "__main__":
    """
        BASIC        = 0    # Basic for Unix and Windows based on signal strength %
        BASIC_IWLIST = 1    # Basic for Unix based on signal RSSI
        SNIFFING     = 2    # Advanced for Unix based on Beacon sniffer

        bg_img takes the form of:
            "path;x_offset;y_offset;scale"
        where (x_offset, y_offset) is the position of (0, 0) point (from left bottom corner)
        and scale is the size in pixels of 1 unit.
    """
    # iface, mode, bg_img = "wlp2s0mon", Scanner.Mode.SNIFFING, "./locations/bram.png;10;10;180"
    iface, mode, bg_img = "Wi-Fi", Scanner.Mode.BASIC, "./locations/william.png;478;973;101"

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("-m", "--mode"):
            mode = int(sys.argv[i+1])
            i += 2
        elif sys.argv[i] in ("-i", "--interface"):
            bg_img = sys.argv[i+1]
            i += 2
        elif sys.argv[i] in ("-bg", "--background"):
            bg_img = sys.argv[i+1]
            i += 2

    wifi_scanner = Scanner(mode=mode, interface=iface, bg_img=bg_img)
    wifi_scanner.start_interactive()
