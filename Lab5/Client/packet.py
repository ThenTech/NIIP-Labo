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
    ADDRREQ  = 0x5
    ADDRACK  = 0x6

    CHECK_VALID = (DISCOVER, DISCACK, MESSAGE, MSGACK, ADDRREQ, ADDRACK)

    __STRINGS = {
        INVALID  : "INVALID",
        DISCOVER : "DISCOVER",
        DISCACK  : "DISCOVER_ACK",
        MESSAGE  : "MESSAGE",
        MSGACK   : "MESSAGE_ACK",
        ADDRREQ  : "ADDRES_REQUEST",
        ADDRACK  : "ADDRES_ACK",
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
        if self.pid:
            attr.append(f"id={Bits.unpack(self.pid)}")
        if self.length:
            attr.append(f"len={self.length}")

        attr.append(f"src={self.source_addr}")
        attr.append(f"dst={self.dest_addr}")

        if self.payload:
            attr.append("data={0}".format(self.payload if self.length < 50 else \
                                          f"({self.length} bytes)"))

        text = "<{0}{1}>" \
            .format(self.name(), " " + ", ".join(attr) if attr else "")

        return style(text, Colours.FG.BLUE)

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
            PacketType.DISCOVER : IPacket,
            PacketType.DISCACK  : IPacket,
            PacketType.MESSAGE  : IPacket,
            PacketType.MSGACK   : IPacket,
            PacketType.ADDRREQ  : IPacket,
            PacketType.ADDRACK  : IPacket,
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
    def create_message_ack(pid, src, dst, payload):
        return IPacket.create(PacketType.MSGACK, pid, src, dst, payload)

    @staticmethod
    def create_address_request(pid, src, dst, payload):
        return IPacket.create(PacketType.ADDRREQ, pid, src, dst, payload)

    @staticmethod
    def create_address_ack(pid, src, dst, payload):
        return IPacket.create(PacketType.ADDRACK, pid, src, dst, payload)


# class Discover(IPacket):
#     def __init__(self, raw=b""):
#         super().__init__(raw)

# class DiscoverAcknowledge(IPacket):
#     def __init__(self, raw=b""):
#         super().__init__(raw)

# class Message(IPacket):
#     """
#     length
#     message id
#     sender addr
#     dest addr
#     payload
#     hopcount
#     """
#     def __init__(self, raw=b""):
#         super().__init__(raw)
