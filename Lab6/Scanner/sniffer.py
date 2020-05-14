from scapy.layers.dot11 import Dot11
from scapy.sendrecv import sniff

from threads import Threading

class Sniffer:
    def __init__(self):
        super().__init__()
        self.access_points = {}
        self.sniffer = None

    def _handle_packet(self, packet) :
        if packet.haslayer(Dot11) :
            if packet.type == 0 and packet.subtype == 8:
                if packet.addr2 not in self.access_points:
                    dump = packet.show(dump=True)
                    self.access_points[packet.addr2] = dump
                    print(f"Access Point MAC: {packet.addr2} with SSID: {packet.info} ")
                    print(dump)

    def _handle_packet_thread(self, interface):
        sniff(iface=interface, prn=self._handle_packet)

    def start(self, interface="Wi-Fi"):
        print("Start sniffing...")
        self.sniffer = Threading.new_thread(self._handle_packet_thread, (interface,))


if __name__ == "__main__":
    """
    https://pythontips.com/2018/09/08/sending-sniffing-wlan-beacon-frames-using-scapy/
    """
    Sniffer().start()
