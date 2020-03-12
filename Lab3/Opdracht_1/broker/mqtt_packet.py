from bits import Bits 
from mqtt_packet_types import *
from mqtt_exceptions import *


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
        # Extract bits, but keep MSB location: shift back to left
        ptype, pflags = (Bits.get(raw[0], 4, 4) << 4), Bits.get(raw[0], 0, 4)
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

    def _extract_next_field(self, length=0, length_bytes=2):
        """For parsing only"""
        if not length:
            blength = int.from_bytes(self.payload[0:length_bytes], "big")
        else:
            blength = length
            length_bytes = 0

        data         = self.payload[length_bytes:length_bytes+blength]
        self.payload = self.payload[length_bytes+blength:]
        return blength, data

    def _includes_packet_identifier(self):
        # If packet_type == PUBLISH and QoS > 0
        if self.ptype == ControlPacketType.PUBLISH:
            flags = ControlPacketType.PublishFlags.from_byte(self.pflag)
            return flags.qos > 0

        if self.ptype in ControlPacketType.CHECK_HAS_PACKET_ID:
            return True

        return False

    def _parse(self, raw):
        # Get type
        self.ptype, self.pflag = self._parse_type(raw)

        if not ControlPacketType.check_flags(self.ptype, self.pflag):
            raise MQTTPacketException("[MQTTPacket::parse] Malformed packet flags for {0}! ({1})"
                                            .format(ControlPacketType.to_string(self.ptype), self.pflag)) 

        # Parse length
        self.length, offset = self._get_length_from_bytes(raw[1:])

        # Everything else is payload
        self.payload = raw[offset + 1:]

        if self._includes_packet_identifier():
            self.packet_id = self.payload[0:2]
            self.payload   = self.payload[2:]

    @staticmethod
    def from_bytes(raw, expected_type=None):
        packet_type, packet_flags = MQTTPacket._parse_type(raw)

        packet_adaptor = {
            ControlPacketType.CONNECT   : Connect,
            ControlPacketType.PUBLISH   : Publish,
            ControlPacketType.SUBSCRIBE : Subscribe,
            ControlPacketType.PUBACK    : MQTTPacket,
            ControlPacketType.PUBREC    : MQTTPacket,
            ControlPacketType.PUBREL    : MQTTPacket,
        }

        if expected_type and packet_type != expected_type:
            return None
        elif packet_type not in packet_adaptor:
            raise MQTTPacketException("[MQTTPacket::from_bytes] Unimplemented packet received! ({0})".format(packet_type))

        return packet_adaptor.get(packet_type, MQTTPacket)(raw)

    @classmethod
    def create(cls, ptype, pflags, payload=bytes()):
        packet = cls()

        if ptype not in ControlPacketType.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket::create] Invalid packet type '{0}'!".format(ptype))
        if pflags not in ControlPacketType.Flags.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket::create] Invalid packet flags '{0}'! (TODO force close connection)".format(pflags))

        packet.ptype = ptype
        packet.pflag = pflags

        if not isinstance(payload, bytes):
            if isinstance(payload, int):
                # if payload is single numeric value
                payload = bytes(tuple(payload))
            elif isinstance(payload, (list, tuple)):
                payload = bytes(payload)
            else:
                raise MQTTPacketException("[MQTTPacket::create] Invalid payload?")

        packet.length  = len(payload)
        packet.payload = payload

        # TODO Check payload contents for variable header or length?

        return packet

    @staticmethod
    def create_connack(session_present, status_code):
        return MQTTPacket.create(ControlPacketType.CONNACK, ControlPacketType.Flags.CONNACK,
                                 bytes((Bits.bit(0, session_present), status_code)))

    @classmethod
    def create_publish(cls, flags, topic_name, payload):
        if not isinstance(flags, ControlPacketType.PublishFlags):
            raise MQTTPacketException("[MQTTPacket::create_publish] Invalid PublishFlags?")

        packet = cls()
        packet.ptype = ControlPacketType.PUBLISH
        packet.pflag = flags.to_bin()

        packet.length = -1
        content = bytearray()
        content.extend(cls._create_length_bytes(len(topic_name)))
        content.extend(topic_name)
        content.extend(cls._create_length_bytes(len(payload)))
        content.extend(payload)
        packet.payload = bytes(content)

        return packet

    @staticmethod
    def create_puback(packet_id):
        return MQTTPacket.create(ControlPacketType.PUBACK, ControlPacketType.Flags.PUBACK, packet_id)

    @staticmethod
    def create_pubrec(packet_id):
        return MQTTPacket.create(ControlPacketType.PUBREC, ControlPacketType.Flags.PUBREC, packet_id)

    @staticmethod
    def create_pubrel(packet_id):
        return MQTTPacket.create(ControlPacketType.PUBREL, ControlPacketType.Flags.PUBREL, packet_id)

    # TODO Other packets

    def to_bin(self):
        data = bytearray()
        data.append(self.ptype | self.pflag)
        if self.length >= 0:
            # If length is given, encode it, else assume its already in payload
            data.extend(self._create_length_bytes(self.length))
        data.extend(self.payload)
        return bytes(data)



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
                 | Bits.bit(6, self.passw)       \
                 | Bits.bit(5, self.will_ret)    \
                 | Bits.bit(3, self.will_qos, 2) \
                 | Bits.bit(2, self.will)        \
                 | Bits.bit(1, self.clean)       \
                 | Bits.bit(0, self.reserved)
            return bytes([bits])

        def is_valid(self):
            return self.reserved == 0 \
               and (   (self.will == 0 and self.will_qos == 0 and self.will_ret == 0) \
                    or (self.will == 1 and self.will_qos in WillQoS.CHECK_VALID)) \
               and (   (self.usr_name == 1) \
                    or (self.usr_name == 0 and self.passw == 0))

        @classmethod
        def from_bytes(cls, raw):
            raw = Bits.to_single_byte(raw)
            return cls(Bits.get(raw, 0), Bits.get(raw, 1), Bits.get(raw, 2), Bits.get(raw, 3, 2),
                       Bits.get(raw, 5), Bits.get(raw, 6), Bits.get(raw, 7))

        def __str__(self):
            flags = []
            if self.clean:
                flags.append("clean")
            if self.will:
                flags.append("will(QoS={0}, Retain={1})".format(self.will_qos, self.will_ret))
            if self.usr_name:
                flags.append("user")
            if self.passw:
                flags.append("pass")

            return "<ConnectFlags: {0}>".format(", ".join(flags))

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

    def _parse_payload(self):
        # To parse the payload for the Connect packet structure, at least 11 bytes are needed (10+)
        if len(self.payload) < 12:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet (too short)!")

        self.protocol_name_length, self.protocol_name = self._extract_next_field()

        print("Protocol name: " + str(self.protocol_name))

        if self.protocol_name_length != 4:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet, unexpected protocol length '{0}'!"
                                            .format(self.protocol_name_length))

        if self.protocol_name != MQTTPacket.PROTOCOL_NAME:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Invalid protocol name '{0}'!".format(self.protocol_name))

        self.protocol_level = int.from_bytes(self.payload[0:1], "big")
        self.connect_flags  = Connect.ConnectFlags.from_bytes(self.payload[1:2])

        if not self.connect_flags.is_valid():
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet flags!")

        # Keep alive time, max val is 0xFFFF == 18 hours, 12 minutes and 15 seconds
        self.keep_alive_s = int.from_bytes(self.payload[2:4], "big")

        self.payload = self.payload[4:]

        # Client ID (1...23 length, or 0 length => assign unique)
        # if len == 0: assign unique and check if clean flag == 0
        #      if clean flag == 0: respond with CONNACK return code 0x02 (Identifier rejected) and close conn
        _, self.packet_id = self._extract_next_field()

        # Will topic
        if self.connect_flags.will:
            _, self.will_topic = self._extract_next_field()

            # Will message
            _, self.will_msg = self._extract_next_field()

        # User name
        if self.connect_flags.usr_name:
            _, self.username = self._extract_next_field()

            # Password
            if self.connect_flags.passw:
                _, self.password = self._extract_next_field()

    def is_valid_protocol_level(self):
        """TODO If False, respond with CONNACK 0x01 : Unacceptable protocol level and disconnect."""
        return self.protocol_level == 4

    def to_bin(self):
        # TODO implement for MQTTClient
        pass


class Subscribe(MQTTPacket):
    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        self.topics = b""
        self.requested_qos = b""
        self._parse_payload()
    
    def _check_flags(self):
        return self.pflag == ControlPacketType.Flags.SUBSCRIBE

    def _parse_payload(self):
        #Get length of topic filter
        topic_len, self.topics = self._extract_next_field()
        print("Subscribing on topic:")
        print(str(self.topics, "utf-8"))

        #Get Requested QOS
        qos_len, self.requested_qos = self._extract_next_field(1)



class Publish(MQTTPacket):
    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        self.pflag = ControlPacketType.PublishFlags.from_byte(self.pflag)
        self.topic = b""
        self.msg   = b""
        self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 4:
            raise MQTTDisconnectError("[MQTTPacket::Publish] Malformed packet (too short)!")

        topic_len, self.topic     = self._extract_next_field()
        id_len   , self.packet_id = self._extract_next_field(length=2)  # TODO overrides client_id?
        # _, self.msg       = self.payload

        if len(self.payload) == self.length - topic_len - id_len:
            print("[MQTTPacket::Publish] Expected size = {0}  vs  actual = {1}".format(self.length - topic_len - id_len, len(self.payload)))
            
    def to_bin(self):
        data = bytearray()
        data.append(self.ptype | self.pflag)

        self.length = len(self.topic) + 2 + len(self.msg)

        data.extend(self._create_length_bytes(self.length))
        data.extend(self._create_length_bytes(len(self.topic)))
        data.extend(self.topic)
        data.extend(self.packet_id)

        if self.msg:
            data.extend(self._create_length_bytes(self.msg))
            data.extend(self.msg)

        return bytes(data)