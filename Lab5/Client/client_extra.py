from packet import ContactRelay
from bits import Bits

import time


class ClientException(Exception):
    pass

class CommunicationType:
    DIRECT_ROUTE  = 1
    OPPORTUNISTIC = 2
    MESH          = 3

    CHOICES = (DIRECT_ROUTE, OPPORTUNISTIC, MESH)

    __STRINGS = {
        DIRECT_ROUTE  : "Direct route",
        OPPORTUNISTIC : "Opportunistic",
        MESH          : "Mesh",
    }

    @staticmethod
    def to_string(ctype):
        return CommunicationType.__STRINGS.get(ctype, f"Unknown? ({ctype})")


class AddressFilterType:
    ALLOW_ALL              = 1
    ONLY_OPPOSITE_EVENNESS = 2

    CHOICES = (ALLOW_ALL, ONLY_OPPOSITE_EVENNESS)

    __STRINGS = {
        ALLOW_ALL              : "Allow all",
        ONLY_OPPOSITE_EVENNESS : "Allow only opposite evenness",
    }

    @staticmethod
    def to_string(atype):
        return AddressFilterType.__STRINGS.get(atype, f"Unknown? ({atype})")


class ContactRelayMetadata:
    def __init__(self, pid, src, dst):
        self.pid      = pid
        self.src      = src
        self.dst      = dst
        self.prev_hop = src
        self.next_hop = -1
        self.is_ack   = False

        self.sent_to   = set()
        self.last_seen = 0

    @classmethod
    def from_packet(cls, packet):
        if not isinstance(packet, ContactRelay):
            raise ClientException("[ContactRelayMetadata] Wrong packet!")

        inst = cls(packet.pid, packet.source_addr, packet.dest_addr)
        inst.prev_hop = packet.prev_hop
        inst.next_hop = packet.next_hop
        inst.is_ack   = packet.length == 0
        return inst

    def __str__(self):
        return f"<Msg{'Ack' if self.is_ack else 'Relay'} " \
             + f"id={Bits.unpack(self.pid)}, " \
             + f"route={self.src}->{self.dst}, hop={self.prev_hop}->{self.next_hop}, " \
             + f"sent={self.sent_to}>"

    def get_key(self):
        return (self.pid, self.src, self.dst, self.is_ack)

    def check_was_sent_to(self, addr):
        return addr in self.sent_to

    def add_sent_to(self, addr):
        self.sent_to.add(addr)
        self.next_hop = addr
        self.last_seen = time.time()

    def clear_sent_to(self):
        self.sent_to = set()
