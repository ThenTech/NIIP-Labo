from bits import Bits
from colours import *

class AddressException(Exception):
    pass

class PacketException(Exception):
    pass


class PacketType:
    INVALID  = 0x0
    DISCOVER = 0x1
    DISCACK  = 0x2
    MESSAGE  = 0x3
    MSGACK   = 0x4

    CONTACT_RELAY     = 0x5
    CONTACT_RELAY_ACK = 0x6

    ROUTE_REQUEST     = 0x7
    ROUTE_REQUEST_ACK = 0x8
    ROUTE_RELAY       = 0x9
    ROUTE_RELAY_ACK   = 0x10

    CHECK_VALID = (
        DISCOVER, DISCACK,
        MESSAGE, MSGACK,
        CONTACT_RELAY, CONTACT_RELAY_ACK,
        ROUTE_REQUEST, ROUTE_REQUEST_ACK, ROUTE_RELAY, ROUTE_RELAY_ACK
    )

    __STRINGS = {
        INVALID           : "INVALID",
        DISCOVER          : "DISCOVER",
        DISCACK           : "DISCOVER_ACK",
        MESSAGE           : "MESSAGE",
        MSGACK            : "MESSAGE_ACK",
        CONTACT_RELAY     : "CONTACT_RELAY",
        CONTACT_RELAY_ACK : "CONTACT_RELAY_ACK",
        ROUTE_REQUEST     : "ROUTE_REQUEST",
        ROUTE_REQUEST_ACK : "ROUTE_REQUEST_ACK",
        ROUTE_RELAY       : "ROUTE_RELAY",
        ROUTE_RELAY_ACK   : "ROUTE_RELAY_ACK",
    }

    @staticmethod
    def to_string(ptype):
        return PacketType.__STRINGS.get(ptype, f"Unknown? ({ptype})")


class IPacket:
    def __init__(self, raw=b""):
        super().__init__()

        self.ptype = PacketType.INVALID
        self.pid   = 0

        self.source_addr = 0
        self.dest_addr   = 0

        self.length  = 0
        self.payload = b""

        if raw:
            self._parse(raw)

        self.transmit_time = 0

    @staticmethod
    def convert_address(addr):
        if isinstance(addr, str):
            try:
                addr = int(addr)
            except:
                raise AddressException(f"Could not parse '{addr}'!")
        elif isinstance(addr, bytes):
            addr = Bits.unpack(addr)

        # Pack into 32 bits
        return Bits.pack(addr, 4)

    ###########################################################################

    def name(self):
        return PacketType.to_string(self.ptype)

    def __str__(self):
        attr = []

        if self.length:
            attr.append(f"len={self.length}")

        attr.append(f"src={self.source_addr}")
        attr.append(f"dst={self.dest_addr}")

        if self.payload:
            attr.append("data={0}".format(self.payload if self.length < 50 else \
                                          f"({self.length} bytes)"))

        text = style(f"<{self.name()} ", Colours.FG.BLUE) \
             + style(f"id={Bits.unpack(self.pid)}", Colours.FG.BRIGHT_BLUE) \
             + style(", " + (", ".join(attr) if attr else "") + ">", Colours.FG.BLUE)

        return text

    ###########################################################################

    @staticmethod
    def _parse_type_length(raw):
        return (raw[0], raw[1]) if len(raw) >= 11 else (0, 0)

    def _parse(self, raw):
        total_length = len(raw)

        if total_length < 11:
            raise PacketException(f"[IPacket::parse] Invalid packet length (too small): {total_length} < 11")

        self.ptype, self.length = IPacket._parse_type_length(raw)
        self.pid                = bytes((raw[2],))
        self.source_addr        = Bits.unpack(raw[3:7])
        self.dest_addr          = Bits.unpack(raw[7:11])
        self.payload            = raw[11:]

        if self.length != len(self.payload):
            raise PacketException(f"[IPacket::parse] Payload length mismatch (expected {self.length} vs {len(self.payload)})")


    @staticmethod
    def from_bytes(raw, expected_type=None):
        packet_type, length = IPacket._parse_type_length(raw)

        if expected_type and packet_type != expected_type:
            return None

        packet_adaptor = {
            PacketType.DISCOVER          : IPacket,
            PacketType.DISCACK           : IPacket,

            PacketType.MESSAGE           : IPacket,
            PacketType.MSGACK            : IPacket,

            PacketType.CONTACT_RELAY     : ContactRelay,
            PacketType.CONTACT_RELAY_ACK : ContactRelayAck,

            PacketType.ROUTE_REQUEST     : RouteRequest,
            PacketType.ROUTE_REQUEST_ACK : RouteRequestAck,
            PacketType.ROUTE_RELAY       : RouteRelay,
            PacketType.ROUTE_RELAY_ACK   : RouteRelayAck,
        }

        if packet_type not in packet_adaptor:
            raise PacketException(f"[IPacket::from_bytes] Unimplemented packet received! ({PacketType.to_string(packet_type)})")

        return packet_adaptor.get(packet_type, IPacket)(raw)

    def to_bin(self):
        if len(self.pid) != 1:
            raise PacketException(f"[IPacket::to_bin] Malformed packet, pid length mismatch!")

        data = bytearray()
        data.append(self.ptype)
        data.append(self.length)
        data.extend(self.pid)
        data.extend(IPacket.convert_address(self.source_addr))
        data.extend(IPacket.convert_address(self.dest_addr))
        data.extend(self.payload)
        return bytes(data)

    @classmethod
    def create(cls, ptype, pid, src, dst, payload=bytes()):
        packet = cls()

        if ptype not in PacketType.CHECK_VALID:
            raise PacketException(f"[IPacket::create] Invalid packet type '{PacketType.to_string(ptype)}'!")

        packet.ptype       = ptype
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        if not isinstance(payload, bytes):
            if isinstance(payload, int):
                # if payload is single numeric value
                payload = bytes(tuple(payload))
            elif isinstance(payload, (list, tuple)):
                payload = bytes(payload)
            else:
                raise PacketException("[IPacket::create] Invalid payload?")

        packet.length  = len(payload)
        packet.payload = payload

        return packet

    @staticmethod
    def create_discover(pid, src, payload):
        return IPacket.create(PacketType.DISCOVER, pid, src, 0, payload)

    @staticmethod
    def create_discover_ack(pid, src, dst, payload):
        return IPacket.create(PacketType.DISCACK, pid, src, dst, payload)

    @staticmethod
    def create_message(pid, src, dst, payload):
        return IPacket.create(PacketType.MESSAGE, pid, src, dst, payload)

    @staticmethod
    def create_message_ack(pid, src, dst):
        return IPacket.create(PacketType.MSGACK, pid, src, dst, b"")

    @staticmethod
    def create_contact_relay(pid, src, dst, next_hop, payload):
        packet = ContactRelay()
        packet.ptype       = PacketType.CONTACT_RELAY
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.prev_hop  = src
        packet.next_hop  = next_hop
        packet.hop_count = 0

        packet.length  = len(payload)
        packet.payload = payload

        return packet

    @staticmethod
    def create_contact_relay_ack(pid, src, dst, next_hop):
        packet = ContactRelayAck()
        packet.ptype       = PacketType.CONTACT_RELAY_ACK
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.prev_hop  = src
        packet.next_hop  = next_hop
        packet.hop_count = 0

        packet.length  = 0
        packet.payload = b""

        return packet

    @staticmethod
    def create_route_request(pid, src, dst, address_list):
        packet = RouteRequest()
        packet.ptype       = PacketType.ROUTE_REQUEST
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.hop_count    = len(address_list)
        packet.address_hops = address_list

        packet.length  = 0
        packet.payload = b""

        return packet

    @staticmethod
    def create_route_request_ack(pid, src, dst, address_list):
        packet = RouteRequestAck()
        packet.ptype       = PacketType.ROUTE_REQUEST_ACK
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.hop_count    = len(address_list)
        packet.address_hops = address_list

        packet.length  = 0
        packet.payload = b""

        return packet

    @staticmethod
    def create_route_relay(pid, src, dst, address_list, payload):
        packet = RouteRelay()
        packet.ptype       = PacketType.ROUTE_RELAY
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.hop_count    = len(address_list)
        packet.address_hops = address_list

        packet.length  = len(payload)
        packet.payload = payload

        return packet

    @staticmethod
    def create_route_relay_ack(pid, src, dst, address_list):
        packet = RouteRelayAck()
        packet.ptype       = PacketType.ROUTE_RELAY_ACK
        packet.pid         = pid
        packet.source_addr = src
        packet.dest_addr   = dst

        packet.hop_count    = len(address_list)
        packet.address_hops = address_list

        packet.length  = 0
        packet.payload = b""

        return packet


class ContactRelay(IPacket):
    def __init__(self, raw=b""):
        super().__init__(raw)

        self.prev_hop  = 0
        self.next_hop  = 0
        self.hop_count = 0

        if raw:
            self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 9:
            raise PacketException(f"[ContactRelay::parse] Invalid payload length (too small): {len(self.payload)} < 9")

        self.prev_hop  = Bits.unpack(self.payload[0:4])
        self.next_hop  = Bits.unpack(self.payload[4:8])
        self.hop_count = self.payload[8]  # Already int (1 element)

        self.payload = self.payload[9:]
        self.length  = len(self.payload)

    def to_bin(self):
        if len(self.pid) != 1:
            raise PacketException(f"[IPacket::to_bin] Malformed packet, pid length mismatch!")

        data = bytearray()
        data.append(self.ptype)
        data.append(self.length + 4 + 4 + 1)   # Adjust for IPacket length (add hop info)
        data.extend(self.pid)
        data.extend(IPacket.convert_address(self.source_addr))
        data.extend(IPacket.convert_address(self.dest_addr))
        data.extend(IPacket.convert_address(self.prev_hop))
        data.extend(IPacket.convert_address(self.next_hop))
        data.append(self.hop_count)
        data.extend(self.payload)
        return bytes(data)

    def __str__(self):
        attr = []

        if self.length:
            attr.append(f"len={self.length}")

        attr.append(f"src={self.source_addr}")
        attr.append(f"dst={self.dest_addr}")

        attr.append(f"hop={self.prev_hop}->{self.next_hop}")
        attr.append(f"hops={self.hop_count}")

        if self.payload:
            attr.append("data={0}".format(self.payload if self.length < 50 else \
                                          f"({self.length} bytes)"))

        text = style(f"<{self.name()} ", Colours.FG.BLUE) \
             + style(f"id={Bits.unpack(self.pid)}", Colours.FG.BRIGHT_BLUE) \
             + style(", " + (", ".join(attr) if attr else "") + ">", Colours.FG.BLUE)

        return text



class ContactRelayAck(ContactRelay):
    def __init__(self, raw=b""):
        super().__init__(raw)


class RouteRequest(IPacket):
    def __init__(self, raw=b""):
        super().__init__(raw)

        self.hop_count    = 0
        self.address_hops = []

        if raw:
            self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 1:
            raise PacketException(f"[RouteRequest::parse] Invalid payload length (too small): {len(self.payload)} < 1")

        self.hop_count = self.payload[0]
        self.payload   = self.payload[1:]

        for offset in range(0, self.hop_count * 4, 4):
            self.address_hops.append(Bits.unpack(self.payload[offset:offset+4]))

        self.payload = self.payload[self.hop_count * 4:]
        self.length  = len(self.payload)

    def get_hop_count(self):
        return len(self.address_hops)

    def get_route(self):
        return self.address_hops

    def get_reverse_route(self):
        return list(reversed(self.get_route()))

    def get_route_string(self):
        return '->'.join(map(str, self.get_route()))

    def get_reverse_route_string(self):
        return '->'.join(map(str, self.get_reverse_route()))

    def add_next_hop(self, addr):
        self.address_hops.append(addr)

    def to_bin(self):
        if len(self.pid) != 1:
            raise PacketException(f"[IPacket::to_bin] Malformed packet, pid length mismatch!")

        self.hop_count = self.get_hop_count()

        data = bytearray()
        data.append(self.ptype)
        data.append(self.length + self.hop_count * 4 + 1)
        data.extend(self.pid)
        data.extend(IPacket.convert_address(self.source_addr))
        data.extend(IPacket.convert_address(self.dest_addr))
        data.append(self.hop_count)

        for a in self.address_hops:
            data.extend(IPacket.convert_address(a))

        data.extend(self.payload)

        return bytes(data)

    def __str__(self):
        attr = []

        if self.length:
            attr.append(f"len={self.length}")

        attr.append(f"src={self.source_addr}")
        attr.append(f"dst={self.dest_addr}")

        if self.address_hops:
            attr.append(f"route={self.get_route_string()}")

        if self.payload:
            attr.append("data={0}".format(self.payload if self.length < 50 else \
                                          f"({self.length} bytes)"))

        text = style(f"<{self.name()} ", Colours.FG.BLUE) \
             + style(f"id={Bits.unpack(self.pid)}", Colours.FG.BRIGHT_BLUE) \
             + style(", " + (", ".join(attr) if attr else "") + ">", Colours.FG.BLUE)

        return text


class RouteRequestAck(RouteRequest):
    def __init__(self, raw=b""):
        super().__init__(raw)

    def get_next_hop_from(self, address):
        try:
            index = self.address_hops.index(address) + 1
        except ValueError:
            return None
        else:
            return self.address_hops[index] if index < len(self.address_hops) else None


class RouteRelay(RouteRequestAck):
    def __init__(self, raw=b""):
        super().__init__(raw)

class RouteRelayAck(RouteRequestAck):
    def __init__(self, raw=b""):
        super().__init__(raw)
