from mqtt.bits import Bits
from mqtt.colours import *
from mqtt.mqtt_packet_types import *
from mqtt.mqtt_exceptions import *
from mqtt.mqtt_subscription import TopicSubscription
from mqtt.topic_matcher import TopicMatcher

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

    def name(self):
        return ControlPacketType.to_string(self.ptype)

    def __str__(self):
        attr = []
        if self.packet_id:
            attr.append("id={0}".format(self.packet_id))
        if self.length:
            attr.append("len={0}".format(self.length))
        text = "<{0}{1}>" \
            .format(self.name(), " " + ", ".join(attr) if attr else "")

        return style(text, Colours.FG.BLUE)

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
            enc, length = length % 128, length // 128

            if length:
                enc |= 128

            len_bytes.append(enc)

        assert(len(len_bytes) <= 4)
        return bytes(len_bytes)

    @staticmethod
    def _get_length_from_bytes(data):
        length, payload_offset = 0, 0
        mult = 1

        if data:
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
            blength = Bits.unpack(self.payload[0:length_bytes])
        else:
            blength = length
            length_bytes = 0

        try:
            data         = self.payload[length_bytes:length_bytes+blength]
            self.payload = self.payload[length_bytes+blength:]
            return blength, data
        except:
            return 0, None


    def _includes_packet_identifier(self):
        # PUBLISH also contains id, but after topic, so not until payload itself
        return self.ptype in ControlPacketType.CHECK_HAS_PACKET_ID

    def _parse(self, raw):
        # Get type
        self.ptype, self.pflag = self._parse_type(raw)

        # If the flags are malformed, disconnect the client
        if not ControlPacketType.check_flags(self.ptype, self.pflag):
            raise MQTTDisconnectError("[MQTTPacket::parse] Malformed packet flags for {0}! ({1})"
                                            .format(self.name(), self.pflag))

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
            ControlPacketType.CONNECT     : Connect,
            ControlPacketType.PUBLISH     : Publish,
            ControlPacketType.SUBSCRIBE   : Subscribe,
            ControlPacketType.UNSUBSCRIBE : Unsubscribe,
            ControlPacketType.PUBACK      : MQTTPacket,
            ControlPacketType.PUBREC      : MQTTPacket,
            ControlPacketType.PUBREL      : MQTTPacket,
            ControlPacketType.PUBCOMP     : MQTTPacket,

            ControlPacketType.PINGREQ     : MQTTPacket,

            ControlPacketType.DISCONNECT  : MQTTPacket,
        }

        if expected_type and packet_type != expected_type:
            return None
        elif packet_type not in packet_adaptor:
            raise MQTTPacketException("[MQTTPacket::from_bytes] Unimplemented packet received! ({0})"
                                        .format(ControlPacketType.to_string(packet_type)))

        return packet_adaptor.get(packet_type, MQTTPacket)(raw)

    @classmethod
    def create(cls, ptype, pflags, payload=bytes()):
        packet = cls()

        if ptype not in ControlPacketType.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket::create] Invalid packet type '{0}'!"
                                            .format(ControlPacketType.to_string(ptype)))
        if pflags not in ControlPacketType.Flags.CHECK_VALID:
            raise MQTTPacketException("[MQTTPacket::create] Invalid packet flags '{0}' (Expected '{1}' for type {2})!"
                                            .format(pflags,
                                                    ControlPacketType.__VALID_FLAGS.get(ptype, "?") if ptype != ControlPacketType.PUBLISH else "*",
                                                    ControlPacketType.to_string(ptype)))

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

        if ptype in ControlPacketType.CHECK_HAS_PACKET_ID and len(payload) == 2:
            # Assume payload is id
            packet.packet_id = payload

        packet.length  = len(payload)
        packet.payload = payload

        return packet

    @staticmethod
    def create_connack(session_present, status_code):
        return MQTTPacket.create(ControlPacketType.CONNACK, ControlPacketType.Flags.CONNACK,
                                 bytes((Bits.bit(0, session_present), status_code)))

    @staticmethod
    def create_publish(flags, packet_id, topic_name, payload):
        if not isinstance(flags, ControlPacketType.PublishFlags):
            raise MQTTPacketException("[MQTTPacket::create_publish] Invalid PublishFlags?")

        packet = Publish()
        packet.ptype     = ControlPacketType.PUBLISH
        packet.pflag     = flags
        packet.packet_id = packet_id
        packet.topic     = topic_name
        packet.payload   = payload
        return packet

    @staticmethod
    def create_puback(packet_id):
        packet_id = Bits.pad_bytes(packet_id, 2)
        return MQTTPacket.create(ControlPacketType.PUBACK, ControlPacketType.Flags.PUBACK, packet_id)

    @staticmethod
    def create_pubrec(packet_id):
        packet_id = Bits.pad_bytes(packet_id, 2)
        return MQTTPacket.create(ControlPacketType.PUBREC, ControlPacketType.Flags.PUBREC, packet_id)

    @staticmethod
    def create_pubrel(packet_id):
        packet_id = Bits.pad_bytes(packet_id, 2)
        return MQTTPacket.create(ControlPacketType.PUBREL, ControlPacketType.Flags.PUBREL, packet_id)

    @staticmethod
    def create_pubcomp(packet_id):
        packet_id = Bits.pad_bytes(packet_id, 2)
        return MQTTPacket.create(ControlPacketType.PUBCOMP, ControlPacketType.Flags.PUBCOMP, packet_id)

    @classmethod
    def create_suback(cls, packet_id, topics_dict):
        packet = cls()
        packet.ptype = ControlPacketType.SUBACK
        packet.pflag = ControlPacketType.Flags.SUBACK
        packet.packet_id = packet_id

        content = bytearray()

        # [MQTT-3.8.4-2] Same Packet Identifier as the SUBSCRIBE Packet
        content.extend(Bits.pad_bytes(packet_id, 2))

        for sub in sorted(topics_dict.values()):
            # Assume success
            content.append(sub.qos if sub.qos in SUBACKReturnCode.CHECK_VALID else SUBACKReturnCode.FAILURE)

        packet.payload = bytes(content)
        packet.length  = len(packet.payload)

        return packet

    @staticmethod
    def create_unsuback(packet_id):
        packet_id = Bits.pad_bytes(packet_id, 2)
        return MQTTPacket.create(ControlPacketType.UNSUBACK, ControlPacketType.Flags.UNSUBACK, packet_id)

    @staticmethod
    def create_pingreq():
        return MQTTPacket.create(ControlPacketType.PINGREQ, ControlPacketType.Flags.PINGREQ)

    @staticmethod
    def create_pingresp():
        return MQTTPacket.create(ControlPacketType.PINGRESP, ControlPacketType.Flags.PINGRESP)

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
            flags.append("clean" if self.clean else "keep")
            flags.append("will(QoS={0}, Retain={1})".format(self.will_qos, self.will_ret) \
                          if self.will else "no will")
            if self.usr_name:
                flags.append("user")
            if self.passw:
                flags.append("pass")

            return style("<{0}>".format(", ".join(flags)), Colours.FG.CYAN)

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

        if raw:
            self._parse_payload()

    def _parse_payload(self):
        # To parse the payload for the Connect packet structure, at least 11 bytes are needed (10+)
        if len(self.payload) < 12:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet (too short)!")

        self.protocol_name_length, self.protocol_name = self._extract_next_field()

        if self.protocol_name_length != 4:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet, unexpected protocol length '{0}'!"
                                            .format(self.protocol_name_length))

        if self.protocol_name != MQTTPacket.PROTOCOL_NAME:
            # [MQTT-3.1.2-1] Invalid protocol, disconnect
            raise MQTTDisconnectError("[MQTTPacket::Connect] Invalid protocol name '{0}'!".format(self.protocol_name))

        self.protocol_level = Bits.unpack(self.payload[0:1])
        self.connect_flags  = Connect.ConnectFlags.from_bytes(self.payload[1:2])

        if not self.connect_flags.is_valid():
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet flags!")

        # Keep alive time, max val is 0xFFFF == 18 hours, 12 minutes and 15 seconds
        self.keep_alive_s = Bits.unpack(self.payload[2:4])

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

            # [MQTT-3.1.2-9] Make sure will topic and msg exist
            if not self.will_topic or not self.will_msg:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Will flag is 1, but no topic or message in packet!")

            # [MQTT-3.1.2-14] Check Will Qos is valid
            if self.connect_flags.will_qos not in WillQoS.CHECK_VALID:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Will flag is 1 and will QoS invalid! ({0})".format(self.connect_flags.will_qos))
        else:
            # [MQTT-3.1.2-13], [MQTT-3.1.2-15]
            if self.connect_flags.will_qos != 0:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Will flag is 0, but the Will QoS is not equal to 0! ({0})".format(self.connect_flags.will_qos))
            if self.connect_flags.will_ret != 0:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Will flag is 0, but the Will Retain is not equal to 0! ({0})".format(self.connect_flags.will_ret))

        # User name
        if self.connect_flags.usr_name:
            _, self.username = self._extract_next_field()

            # [MQTT-3.1.2-19] If username not present
            if not self.username:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Username flag is 1, but no username given!")

            # Password
            if self.connect_flags.passw:
                _, self.password = self._extract_next_field()

                # [MQTT-3.1.2-21] If password not present
                if not self.password:
                    raise MQTTDisconnectError("[MQTTPacket::Connect] Password flag is 1, but no password given!")
            else:
                # [MQTT-3.1.2-20] Password flag == 0, no password in payload allowed
                _, pw = self._extract_next_field()
                if pw:
                    raise MQTTDisconnectError("[MQTTPacket::Connect] Password flag is 0, but password given!")
        else:
            _, un = self._extract_next_field()

            # [MQTT-3.1.2-18] User flag == 0, no username in payload allowed
            if un != None and self.username != b"":
                raise MQTTDisconnectError("[MQTTPacket::Connect] Username given while flag was set to 0 (MQTT-3.1.2-18)")

            # [MQTT-3.1.2-22] No username, means no password allowed.
            if self.connect_flags.passw:
                raise MQTTDisconnectError("[MQTTPacket::Connect] Username flag is 0, but password flag is set!")

    def is_valid_protocol_level(self):
        """TODO If False, respond with CONNACK 0x01 : Unacceptable protocol level and disconnect."""
        return self.protocol_level == 4

    def to_bin(self):
        # TODO implement for MQTTClient
        pass

    def __str__(self):
        attr = []

        if self.protocol_name:
            attr.append("prot={0}".format(self.protocol_name))
        if self.protocol_level:
            attr.append("plvl={0}".format(self.protocol_level))
        if self.keep_alive_s:
            attr.append("KeepAlive={0}s".format(self.keep_alive_s))
        if self.packet_id:
            attr.append("id='{0}'".format(self.packet_id))
        if self.will_topic:
            attr.append("wtop={0}".format(Bits.bytes_to_str(self.will_topic)))
        if self.will_msg:
            attr.append("wmsg={0}".format(self.will_msg))
        if self.username:
            attr.append("usr={0}".format(self.username))
        if self.password:
            attr.append("psw={0}".format(self.password))

        text = style("<{0}".format(self.name()), Colours.FG.BLUE)
        if self.connect_flags:
            text += style(" conn=", Colours.FG.BLUE)
            text += str(self.connect_flags)
        if attr:
            text2 = " " if not self.connect_flags else ", "
            text2 += ", ".join(attr)
            text += style(text2, Colours.FG.BLUE)
        text += style(">", Colours.FG.BLUE)

        return text

class Subscribe(MQTTPacket):
    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        self.topics = {}  # { topic: TopicSubscription(order, topic, qos) }
        if raw:
            self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 3:
            # Also covers [MQTT-3.8.3-3]: At least one topic is required.
            raise MQTTDisconnectError("[MQTTPacket::Subscribe] Malformed packet (too short)!")

        # Already got packet_id, if there was one

        subscription_order = 0

        # Payload contains one or more topics followed by a QoS
        while len(self.payload) > 0:
            # Get topic filter
            topic_len, topic = self._extract_next_field()

            if topic_len < 1:
                # [MQTT-4.7.3-1] Topic needs to be at least 1 byte long
                raise MQTTPacketException("[MQTTPacket::Subscribe] Topic must be at least 1 character long!")
            elif b"\x00" in topic:
                # [MQTT-4.7.3-2] Topic cannot contain null characters
                raise MQTTPacketException("[MQTTPacket::Subscribe] Topic may not contain null characters!")

            # Get Requested QOS
            qos_len, qos = self._extract_next_field(1)
            qos = Bits.unpack(qos)

            if qos not in WillQoS.CHECK_VALID:
                raise MQTTDisconnectError("[MQTTPacket::Subscribe] Malformed QoS!")

            # [MQTT-2.3.1-1] If qos > 0 then packet_id (!= 0) is required
            if qos > 0 and (not self.packet_id or (self.packet_id and Bits.unpack(self.packet_id) == 0)):
                raise MQTTPacketException("[MQTTPacket::Subscribe] Topic QoS level > 0, but no or zeroed Packet ID given!")

            # WARNING The order is important, SUBACK needs to send in same order
            sub = TopicSubscription(subscription_order, Bits.bytes_to_str(topic), qos)
            subscription_order += 1
            self.topics[sub.topic] = sub

    def to_bin(self):
        # TODO implement for MQTTClient
        pass

    def __str__(self):
        attr = []
        if self.packet_id:
            attr.append("id={0}".format(self.packet_id))
        if self.topics:
            attr.append("topics=[{0}]".format(", ".join(map(str, self.topics.values()))))

        return style("<{0}{1}>" \
                        .format(self.name(),
                                " " + ", ".join(attr) if attr else ""),
                    Colours.FG.BLUE)


class Unsubscribe(MQTTPacket):
    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        self.topics = []  # [ topics ]
        if raw:
            self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 3:
            # Also covers [MQTT-3.10.3-2]: At least one topic is required.
            raise MQTTDisconnectError("[MQTTPacket::Unsubscribe] Malformed packet (too short)!")

        # [MQTT-2.3.1-1] If qos > 0 then packet_id (!= 0) is required
        # `self.pflag.qos > 0 and`  =>  Cannot check flags here, no flags!
        # Unsubscribe always has packet id!
        if (not self.packet_id or (self.packet_id and Bits.unpack(self.packet_id) == 0)):
            raise MQTTPacketException("[MQTTPacket::Unsubscribe] QoS level > 0, but no or zeroed Packet ID given!")

        # Payload contains one or more topics followed by a QoS
        while len(self.payload) > 0:
            # Get topic filter
            topic_len, topic = self._extract_next_field()

            if topic_len < 1:
                # [MQTT-4.7.3-1] Topic needs to be at least 1 byte long
                raise MQTTPacketException("[MQTTPacket::Unsubscribe] Topic must be at least 1 character long!")
            elif b"\x00" in topic:
                # [MQTT-4.7.3-2] Topic cannot contain null characters
                raise MQTTPacketException("[MQTTPacket::Unsubscribe] Topic may not contain null characters!")

            self.topics.append(Bits.bytes_to_str(topic))

    def to_bin(self):
        # TODO implement for MQTTClient
        pass

    def __str__(self):
        attr = []
        if self.packet_id:
            attr.append("id={0}".format(self.packet_id))
        if self.topics:
            attr.append("topics={0}".format(self.topics))

        return style("<{0}{1}>" \
                        .format(self.name(),
                                " " + ", ".join(attr) if attr else ""),
                    Colours.FG.BLUE)

class Publish(MQTTPacket):
    def __init__(self, raw=b''):
        super().__init__(raw=raw)
        self.pflag = ControlPacketType.PublishFlags.from_byte(self.pflag)
        self.topic = b""
        if raw:
            self._parse_payload()

    def _parse_payload(self):
        if len(self.payload) < 4:
            raise MQTTDisconnectError("[MQTTPacket::Publish] Malformed packet (too short)!")
        topic_len, id_len = 0, 0

        topic_len, self.topic = self._extract_next_field()

        if topic_len < 1:
            # [MQTT-4.7.3-1] Topic needs to be at least 1 byte long
            raise MQTTPacketException("[MQTTPacket::Publish] Topic must be at least 1 character long!")

        # [MQTT-3.3.2-2] Topic cannot contain wildcards
        # [MQTT-4.7.3-2] Topic cannot contain null characters
        top = Bits.bytes_to_str(self.topic)
        if TopicMatcher.HASH in top or TopicMatcher.PLUS in top or b'\x00' in self.topic:
            raise MQTTPacketException("[MQTTPacket::Publish] Topic may not contain wildcards or null characters!")

        if self.pflag.qos in (WillQoS.QoS_1, WillQoS.QoS_2):
            # TODO overrides client_id?
            id_len, self.packet_id = self._extract_next_field(length=2)

            # [MQTT-2.3.1-1] If qos > 0 then packet_id (!= 0) is required
            if not self.packet_id or (self.packet_id and Bits.unpack(self.packet_id) == 0):
                raise MQTTPacketException("[MQTTPacket::Publish] QoS level > 0, but no or zeroed Packet ID given!")
        elif self.pflag.qos == WillQoS.QoS_0 and self.packet_id:
            # [MQTT-2.3.1-5]
            raise MQTTPacketException("[MQTTPacket::Publish] QoS level == 0, but Packed ID given! ({0})".format(self.packet_id))

        if len(self.payload) == self.length - topic_len - id_len:
            print("[MQTTPacket::Publish] Expected size = {0}  vs  actual = {1}"
                    .format(self.length - topic_len - id_len, len(self.payload)))

    def to_bin(self):
        data = bytearray()
        data.append(self.ptype | self.pflag.to_bin())

        msg = bytearray()
        msg.extend(Bits.pack(len(self.topic), 2))
        msg.extend(self.topic)

        if self.pflag.qos in (WillQoS.QoS_1, WillQoS.QoS_2):
            msg.extend(Bits.pad_bytes(self.packet_id, 2))

        if self.payload:
            msg.extend(self.payload)

        self.length = len(msg)
        data.extend(self._create_length_bytes(self.length))
        data.extend(msg)

        return bytes(data)

    def __str__(self):
        attr = []
        attr.append("id={0}".format(self.packet_id or "?"))
        if self.topic:
            attr.append("topic='{0}'".format(Bits.bytes_to_str(self.topic)))
        if self.payload:
            attr.append("msg={0}".format(self.payload if len(self.payload) < 100 else \
                                           "({0} bytes)".format(len(self.payload))))

        return style("<{0}".format(self.name()), Colours.FG.BLUE) \
             + str(self.pflag) \
             + (style(" " + ", ".join(attr), Colours.FG.BLUE) if attr else "") \
             + style(">", Colours.FG.BLUE)
