from access_points import get_scanner
from colours import *
import traceback

class Scanner:
    def __init__(self):
        super().__init__()
        self.scanner = get_scanner()
        self.access_points = {}

    def __str__(self):
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

    def sample(self):
        # Calls on windows: `netsh wlan show networks mode=bssid`
        aps = self.scanner.get_access_points()

        if not aps:
            self._log(style("No Access Points in range or no WLAN interface available!", Colours.FG.BRIGHT_RED))
            return

        self._log(f"Updated info for {len(aps)} access points.")
        self.access_points.update(self.aps_to_dict(aps))

    @staticmethod
    def aps_to_dict(aps):
        return { (ap['ssid'], ap['bssid']) : ap['quality'] for ap in aps}


    @staticmethod
    def _calc_intersetion(x1, y1, r1, x2, y2, r2, x3, y3, r3):
        """https://www.101computing.net/cell-phone-trilateration-algorithm/"""

        A = 2 * x2 - 2 * x1
        B = 2 * y2 - 2 * y1
        C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
        D = 2 * x3 - 2 * x2
        E = 2 * y3 - 2 * y2
        F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2
        x = (C*E - F*B) / (E*A - B*D)
        y = (C*D - A*F) / (B*D - A*E)

        return x, y

    ###########################################################################

    @staticmethod
    def _handle_print(self):
        print(self)

    @staticmethod
    def _handle_sample(self):
        try:
            self.sample()
        except Exception as e:
            self._err(e, "Sampling ")

    @staticmethod
    def _handle_clear(self):
        self.access_points = {}
        self.lowest_quality, self.highest_quality = "", ""

    @staticmethod
    def _handle_exit(self):
        exit(0)


class Commands:
    PRINT_CURRENT = "print"
    SAMPLE        = "sample"
    CLEAR         = "clear"
    EXIT          = "exit"

    CHOICES = ( PRINT_CURRENT, SAMPLE, CLEAR, EXIT )

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
            Commands.CLEAR         : scanner._handle_clear,
            Commands.EXIT          : scanner._handle_exit,
        }

        handler.get(cmd)(scanner)


if __name__ == "__main__":
    """
    Considerations:
        - Add live plot mapping RSSI for all APs that were detected at one point?
        - 2D representation of AP locations (unknown?) and RSSI as circles
            -> intersection with _calc_intersetion() represents device location
        - Something like: https://github.com/kootenpv/whereami
    """

    wifi_scanner = Scanner()

    print(style("Command list:", Colours.FG.BLACK, Colours.BG.YELLOW) + " " + ", ".join(Commands.CHOICES))

    while True:
        raw = input("Enter command: ")
        Commands.handle_cmd(raw, wifi_scanner)
