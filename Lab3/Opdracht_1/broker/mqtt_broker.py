import socket

# Bit helpers
class Bits:
    @staticmethod
    def bit(idx, val, size = 1):
        val = val & ((1 << size) - 1)
        return (val << idx)

    @staticmethod
    def get(val, idx, size = 1):
        return ((val >> idx) & ((1 << size) - 1))

    @staticmethod
    def to_single_byte(raw):
        if isinstance(raw, bytes):
            return int(raw[0])
        return raw


class MQTTPacketException(Exception):
    pass


class ControlPacketType:
    _RESERVED1  = 0x00
    CONNECT     = 0x10   # Client -> Server  : Client request to connect to Server
    CONNACK     = 0x20   # Server -> Client  : Connect acknowledgement
    PUBLISH     = 0x30   # Client <-> Server : Publish message
    PUBACK      = 0x40   # Client <-> Server : Publish acknowledgment
    PUBREC      = 0x50   # Client <-> Server : Publish received (assured delivery part 1)
    PUBREL      = 0x60   # Client <-> Server : Publish release (assured delivery part 2)
    PUBCOMP     = 0x70   # Client <-> Server : Publish complete (assured delivery part 3)
    SUBSCRIBE   = 0x80   # Client -> Server  : Client subscribe request
    SUBACK      = 0x90   # Server -> Client  : Subscribe acknowledgment
    UNSUBSCRIBE = 0xA0   # Client -> Server  : Unsubscribe request
    UNSUBACK    = 0xB0   # Server -> Client  : Unsubscribe acknowledgment
    PINGREQ     = 0xC0   # Client -> Server  : PING request
    PINGRESP    = 0xD0   # Server -> Client  : PING response
    DISCONNECT  = 0xE0   # Client -> Server  : Client is disconnecting
    _RESERVED2  = 0xF0

    CHECK_VALID   = (CONNECT, CONNACK, PUBLISH, PUBACK, PUBREC,
                     PUBREL, PUBCOMP, SUBSCRIBE, SUBACK, UNSUBSCRIBE,
                     UNSUBACK, PINGREQ, PINGRESP, DISCONNECT)
    CHECK_INVALID = (_RESERVED1, _RESERVED2)

    CHECK_CLIENT_TO_SERVER = (CONNECT, PUBLISH, PUBACK, PUBREC, PUBREL,
                              PUBCOMP, SUBSCRIBE, UNSUBSCRIBE, PINGREQ, DISCONNECT)
    CHECK_SERVER_TO_CLIENT = (CONNACK, PUBLISH, PUBACK, PUBREC, PUBREL,
                              PUBCOMP, SUBACK, UNSUBACK, PINGRESP)

    CHECK_HAS_PACKET_ID = (PUBACK, PUBREC, PUBREL, PUBCOMP,
                           SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK)

    CHECK_PAYLOAD_REQUIRED = (CONNECT, SUBSCRIBE, SUBACK, UNSUBSCRIBE)
    CHECK_PAYLOAD_OPTIONAL = (PUBLISH)
    CHECK_PAYLOAD_NONE     = (CONNACK, PUBACK, PUBREC, PUBREL, PUBCOMP, UNSUBACK, PINGREQ, PINGRESP, DISCONNECT)


    class PublishFlags:
        def __init__(self, DUP=0, QoS=0, RETAIN=0):
            """
            DUP    : Duplicate delivery of a PUBLISH Control Packet
            QoS    : PUBLISH Quality of Service
            RETAIN : PUBLISH Retain flag
            """
            super().__init__()
            self.dup    = DUP
            self.qos    = QoS
            self.retain = RETAIN

        @classmethod
        def from_byte(cls, raw):
            dup, qos, ret = Bits.get(raw, 4), Bits.get(raw, 1, 2), Bits.get(raw, 0)
            return cls(dup, qos, ret)

        def to_bin(self):
            return Bits.bit(3, self.DUP)    \
                 | Bits.bit(1, self.QoS, 2) \
                 | Bits.bit(0, self.RETAIN)

    class Flags:
        CONNECT     = 0x00  # Reserved
        CONNACK     = 0x00  # Reserved
        PUBLISH     = 0x00  # Use PublishFlags
        PUBACK      = 0x00  # Reserved
        PUBREC      = 0x00  # Reserved
        PUBREL      = 0x02
        PUBCOMP     = 0x00
        SUBSCRIBE   = 0x02
        SUBACK      = 0x00
        UNSUBSCRIBE = 0x02
        UNSUBACK    = 0x00
        PINGREQ     = 0x00
        PINGRESP    = 0x00
        DISCONNECT  = 0x00

        CHECK_VALID = (CONNECT, CONNACK, PUBLISH, PUBACK, PUBREC, PUBREL,
                       PUBCOMP, SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK, PINGREQ, PINGRESP, DISCONNECT)

class WillQoS:
    QoS_0 = 0x0
    QoS_1 = 0x1
    QoS_2 = 0x2
    QoS_3 = 0x3

    CHECK_VALID = (QoS_0, QoS_1, QoS_2)


class MQTTPacket:
    PROTOCOL_NAME = b"MQTT"

    def __init__(self, raw=b""):
        super().__init__()

        self.ptype = 0
        self.pflag = 0

        self.length = 0

        self.packet_id = b""
        self.payload   = b""

        if raw:
            self._parse(raw)

    @staticmethod
    def _parse_type(raw):
        ptype, pflags = Bits.get(raw[0], 4, 4), Bits.get(raw[0], 0, 4)
        return ptype, pflags

    @staticmethod
    def _create_length_bytes(length):
        if length <= 0x7F:  # 127
            return bytes((length,))
        elif length > 268435455:
            # Larger than 256Mb
            raise MQTTPacketException("[MQTTPacket] Payload exceeds maximum length (256Mb)!")

        len_bytes = bytearray()

        while length > 0:
            enc, length = length % 128, length / 128

            if length:
                enc |= 128

            len_bytes.append(enc)

        assert(len(len_bytes) <= 4)
        return bytes(len_bytes)

    @staticmethod
    def _get_length_from_bytes(data):
        length, payload_offset = 0, 0
        mult = 1

        while True:
            enc = data[payload_offset]

            length += (enc & 127) * mult
            mult *= 128
            payload_offset += 1

            if mult > 2097152:
                # More than 4 bytes parsed, error
                raise MQTTPacketException("[MQTTPacket] Malformed remaining length!")

            if (enc & 128) == 0:
                break

        return length, payload_offset

    def _includes_packet_identifier(self):
        # If packet_type == PUBLISH and QoS > 0
        if self.control_packet_type == ControlPacketType.PUBLISH:
            flags = ControlPacketType.PublishFlags.from_byte(self.pflag)
            return flags.qos > 0

        if self.control_packet_type in ControlPacketType.CHECK_HAS_PACKET_ID:
            return True

        return False

    def _parse(self, raw):
        # Get type
        self.control_packet_type, self.control_packet_flag = self._parse_type(raw)

        # Parse length
        self.packet_length, offset = self._get_length_from_bytes(raw[1:])

        # Everything else is payload
        self.payload = raw[offset:]

        if self._includes_packet_identifier():
            self.packet_id = self.payload[0:2]
            self.payload = self.payload[2:]

    @staticmethod
    def from_bytes(raw):
        packet_type, packet_flags = MQTTPacket._parse_type(raw)

        packet_adaptor = {
            ControlPacketType.CONNECT: Connect,
        }

        return packet_adaptor.get(packet_type, MQTTPacket)(raw)

    @classmethod
    def create(cls, ptype, pflags, length, payload):
        packet = cls()

        if ptype not in ControlPacketType.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket] Invalid packet type '{0}'!".format(ptype))
        if pflags not in ControlPacketType.Flags.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket] Invalid packet flags '{0}'! (TODO force close connection)".format(pflags))

        packet.control_packet_type = ptype
        packet.control_packet_flag = pflags

        packet.packet_length = len(payload)
        packet.payload = payload

        # TODO Check payload contents for variable header or length?

        return packet


    def to_bin(self):
        data = bytearray()
        data.append(self.ptype << 4 | self.pflag)
        data.append(self._create_length_bytes(self.length))
        data.extend(self.payload)
        return data


class Connect(MQTTPacket):
    class ConnectFlags:
        def __init__(self, reserved=1, clean=0, will=0, will_qos=0, will_ret=0, passw=0, usr_name=0):
            super().__init__()
            self.reserved = reserved
            self.clean    = clean       # If 0, store and restore the session with same client, else always create new session.
            self.will     = will        # If 1, publish Will message on error/disconnect, else don't
            self.will_qos = will_qos    # If will==0 then 0, else if will==1 then qos in WillQoS.CHECK_VALID
            self.will_ret = will_ret    # If will==0 then 0, else if will==1 then if ret == 0: Publish Will msg as non-retained, else retained.
            self.passw    = passw       # If usr_name==0, then 0, else if passw==1, password must be in payload, else not
            self.usr_name = usr_name    # If 1, user name must be in payload, else not

        def byte(self):
            bits = Bits.bit(7, self.usr_name)    \
                 | Bits.bit(6, self.passw)        \
                 | Bits.bit(5, self.will_ret)    \
                 | Bits.bit(3, self.will_qos, 2) \
                 | Bits.bit(2, self.will)        \
                 | Bits.bit(1, self.clean)       \
                 | Bits.bit(0, self.reserved)
            return bytes([bits])

        def is_valid(self):
            return self.reserved == 0 \
               and (   (self.will == 0 and self.will_qos == 0) \
                    or (self.will == 1 and self.will_qos in WillQoS.CHECK_VALID)) \
               and (   (self.will == 0 and self.will_ret == 0) ) \
               and (   (self.usr_name == 0 and self.passw == 0))

        @classmethod
        def from_bytes(cls, raw):
            raw = Bits.to_single_byte(raw)
            return cls(Bits.get(raw, 0), Bits.get(raw, 1), Bits.get(raw, 2), Bits.get(raw, 3, 2),
                       Bits.get(raw, 5), Bits.get(raw, 6), Bits.get(raw, 7))


    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        # Connect header
        self.protocol_name_length = 0
        self.protocol_name        = b""
        self.protocol_level       = 0
        self.connect_flags        = None
        self.keep_alive_s         = 0

        # Payload
        self.packet_id  = b""
        self.will_topic = b""
        self.will_msg   = b""
        self.username   = b""
        self.password   = b""

        self._parse_payload()

    def _extract_next_field(self, length=0, length_bytes=2):
        blength      = int.from_bytes(self.payload[0:length_bytes], "big") if not length else length
        data         = self.payload[length_bytes:length_bytes+blength]
        self.payload = self.payload[length_bytes+blength:]
        return blength, data

    def _parse_payload(self):
        # To parse the payload for the Connect packet structure, at least 11 bytes are needed (10 +)
        if len(self.payload) < 12:
            raise MQTTPacketException("[MQTTPacket::Connect] Malformed packet (too short)! (TODO disconnect)")

        self.protocol_name_length, self.protocol_name = self._extract_next_field()

        if self.protocol_name_length != 4:
            raise MQTTPacketException("[MQTTPacket::Connect] Malformed packet, unexpected protocol length '{0}'! (TODO disconnect)"
                                            .format(self.protocol_name_length))

        if self.protocol_name != MQTTPacket.PROTOCOL_NAME:
            raise MQTTPacketException("[MQTTPacket::Connect] Invalid protocol name '{0}'! (TODO disconnect)".format(self.protocol_name))

        self.protocol_level = int(self.payload[0:1])
        self.connect_flags  = Connect.ConnectFlags.from_bytes(self.payload[1:2])

        if not self.connect_flags.is_valid():
            raise MQTTPacketException("[MQTTPacket::Connect] Malformed packet flags! (TODO disconnect)")

        # Keep alive time, max val is 0xFFFF == 18 hours, 12 minutes and 15 seconds
        self.keep_alive_s = int.from_bytes(self.payload[2:4], "big")

        self.payload = self.payload[4:]

        # Client ID (1...23 length, or 0 length => assign unique)
        # if len == 0: assign unique and check if clean flag == 1
        #      if clean flag == 1: respond with CONNACK return code 0x02 (Identifier rejected) and close conn
        _, self.packet_id = self._extract_next_field()

        # Will topic
        if self.connect_flags.will:
            _, self.will_topic = self._extract_next_field()

            # Will message
            _, self.will_msg = self._extract_next_field()

        # User name
        if self.connect_flags.usr_name:
            _,self.username = self._extract_next_field()

            # Password
            if self.connect_flags.passw:
                _, self.password = self._extract_next_field()

    def is_valid_protocol_level(self):
        """TODO If False, respond with CONNACK 0x01 : Unacceptable protocol level and disconnect."""
        return self.protocol_level == 4






##########################################################################################
#### Server

class MQTTBroker:
    HOST     = "10.42.0.252"
    PORT     = 1883
    PORT_SSL = 1883

    def __init__(self, host=HOST, port=PORT, use_ssl=False):
        super().__init__()
        self.host = host
        self.port = PORT_SSL if use_ssl else port

        self.serverSocket = None
        self.init_socket()
        self.listen_incoming()

    def init_socket(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.listen(5)

    def listen_incoming(self):
        while True:
            (clientSocket, address) = self.serverSocket.accept()
            msg = clientSocket.recv()
            print(msg)


##########################################################################################
#### Client

class MQTTClient:
    pass



broker = MQTTBroker()
