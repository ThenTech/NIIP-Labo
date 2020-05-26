from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11ProbeReq, Dot11ProbeResp, RadioTap
from scapy.sendrecv import sniff

from access_points_enhanced import AccessPoint

from colours import Colours, style
from threads import Threading


class Bits:
    @staticmethod
    def bytes_to_str(bytestr):
        try:
            return str(bytestr, "utf-8") if not isinstance(bytestr, str) \
                else bytestr
        except:
            return bytestr


class PacketTypes:
    PROBE_REQ  = (0, 4)
    PROBE_RESP = (0, 5)
    BEACON     = (0, 8)

    __STRINGS = {
        PROBE_REQ  : "PROBE_REQ",
        PROBE_RESP : "PROBE_RESP",
        BEACON     : "BEACON",
    }

    # This includes: CTS, ACK, Data + CF-Poll, ...
    __IGNORE = ((1, 12), (1, 13), (2, 4), (1,11), (0,13), (1,9))

    @classmethod
    def all(cls):
        return (cls.PROBE_REQ, cls.PROBE_RESP, cls.BEACON)

    @classmethod
    def to_string(cls, ptype):
        return cls.__STRINGS.get(ptype, f"{ptype}")

    @staticmethod
    def has_correct_layer(packet):
        return any(map(packet.haslayer, (Dot11, Dot11Beacon, Dot11ProbeReq, Dot11ProbeResp, RadioTap)))

    @classmethod
    def is_ignored_type(cls, ptype):
        return ptype in cls.__IGNORE


class Sniffer:
    def __init__(self, interface="wlp2s0mon"):
        super().__init__()
        self.interface = interface
        self.sniffer   = None

        self.access_points = {}  # { mac: AccessPoint() }
        self.aps_lock = Threading.new_lock()

    def _log(self, msg):
        print(style(f"[Sniffer]", Colours.FG.YELLOW), msg)

    def _handle_packet(self, packet) :
        if not PacketTypes.has_correct_layer(packet):
            return

        mac, ptype = packet.addr2 if hasattr(packet, "addr2") else None, \
                     (packet.type, packet.subtype)

        if PacketTypes.is_ignored_type(ptype):
            return

        if mac and ptype in PacketTypes.all():
            # dump = packet.show(dump=True)

            rssi = 255
            if packet.haslayer(RadioTap):
                radiotap = packet.getlayer(RadioTap)
                rssi = float(radiotap.dBm_AntSignal)
            else:
                self._log(style(f"Could not get RSSI value from packet with type {PacketTypes.to_string(ptype)}!", Colours.FG.BRIGHT_RED) \
                        + " (" + packet.summary() + ")")
                return

            with self.aps_lock:
                if mac not in self.access_points:
                    ap = AccessPoint(ssid=Bits.bytes_to_str(packet.info), bssid=packet.addr2.upper(), quality=rssi, security="")
                    self.access_points[mac] = ap
                    self._log(f"New Access Point @ {ap.bssid} '{ap.ssid}' (from {packet.summary()})")
                else:
                    self.access_points[mac].quality = rssi
        else:
            pass
            # self._log(style(f"Packet has correct layer but wrong type {PacketTypes.to_string(ptype)}?", Colours.FG.BRIGHT_RED) \
            #         + packet.summary())

    def _handle_packet_thread(self):
        try:
            try:
                sniff(iface=self.interface, prn=self._handle_packet, monitor=True)
            except OSError:
                sniff(iface=self.interface, prn=self._handle_packet)
        except Exception as e:
            self._log(style(f"{e}", Colours.FG.BRIGHT_RED))

    def start(self):
        self._log("Start sniffing...")
        self.sniffer = Threading.new_thread(self._handle_packet_thread, daemon=True)

    def get_access_points(self):
        # Returns [ AccessPoint()... ]
        with self.aps_lock:
            return [ ap.copy() for ap in self.access_points.values()]

if __name__ == "__main__":
    """
    https://pythontips.com/2018/09/08/sending-sniffing-wlan-beacon-frames-using-scapy/
    """
    Sniffer().start()
