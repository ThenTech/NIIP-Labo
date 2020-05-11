from access_points import get_scanner
from colours import *

class Scanner:
    def __init__(self):
        super().__init__()
        self.scanner = get_scanner()
        self.access_points = {}

        self.lowest_quality  = ""
        self.highest_quality = ""

    def __str__(self):
        choose_colour = lambda key: Colours.FG.BRIGHT_RED   if key == self.lowest_quality  else \
                                    Colours.FG.BRIGHT_GREEN if key == self.highest_quality else \
                                    Colours.FG.WHITE
        printed = "\n".join(f"{style(k, Colours.FG.YELLOW)}: {style(v, choose_colour(k))}" for k, v in self.access_points) \
                    if self.access_points else style("No APs sampled! Run sample command first.", Colours.FG.BRIGHT_RED)

        return style("Scanner Access Points:", Colours.FG.YELLOW) + "\n" + printed

    def _log(self, msg):
        print(style(f"[Scanner]", Colours.FG.YELLOW), msg)

    def sample(self):
        aps = self.scanner.get_access_points()

        if not aps:
            self._log(style("No Access Points in range or no WLAN interface available!", Colours.FG.BRIGHT_RED))
            return

        self.access_points.update(self.aps_to_dict(aps))

        low, high = 100, -100
        self.lowest_quality, self.highest_quality = "", ""

        for ssid, quality in self.access_points:
            if quality <= low:
                low = quality
                self.lowest_quality = ssid
            elif quality >= high:
                high = quality
                self.highest_quality = ssid

    @staticmethod
    def aps_to_dict(aps):
        return {ap['ssid'] + " " + ap['bssid']: ap['quality'] for ap in aps}

    @staticmethod
    def _handle_print(self):
        print(self)

    @staticmethod
    def _handle_sample(self):
        self.sample()

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
    wifi_scanner = Scanner()

    print(style("Command list:", Colours.FG.BLACK, Colours.BG.YELLOW) + " " + ", ".join(Commands.CHOICES))

    while True:
        raw = input("Enter command: ")
        Commands.handle_cmd(raw, wifi_scanner)
