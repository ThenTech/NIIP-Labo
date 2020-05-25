from scapy.layers.dot11 import Dot11
from scapy.sendrecv import sniff

from access_points_enhanced import AccessPoint

from colours import Colours, style
from threads import Threading

class Sniffer:
    def __init__(self, interface="wlp2s0"):
        super().__init__()
        self.interface = interface
        self.sniffer   = None

        self.access_points = {}
        self.aps_lock = Threading.new_lock()


    def _log(self, msg):
        print(style(f"[Scanner]", Colours.FG.YELLOW), msg)

    def _handle_packet(self, packet) :
        if packet.haslayer(Dot11) :
            if packet.type == 0 and packet.subtype == 8:
                if packet.addr2 not in self.access_points:
                    dump = packet.show(dump=True)
                    self.access_points[packet.addr2] = packet
                    self._log(f"Access Point MAC: {packet.addr2} with SSID: {packet.info}\n{dump}")

    def _handle_packet_thread(self, interface):
        sniff(iface=self.interface, prn=self._handle_packet)

    def start(self):
        self._log("Start sniffing...")
        self.sniffer = Threading.new_thread(self._handle_packet_thread, daemon=True)

    def get_access_points(self):
        results = []  # [ AccessPoint()... ]

        with self.aps_lock:
            for k, packet in self.access_points.items():
                results.append(AccessPoint(ssid=packet.info, bssid=k, quality=0, security=""))

        return results

if __name__ == "__main__":
    """
    https://pythontips.com/2018/09/08/sending-sniffing-wlan-beacon-frames-using-scapy/
    """
    Sniffer().start()
