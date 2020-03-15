from mqtt.bits import Bits
from mqtt.colours import *

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

    __STRINGS = {
        _RESERVED1  : "_RESERVED1",
        CONNECT     : "CONNECT",
        CONNACK     : "CONNACK",
        PUBLISH     : "PUBLISH",
        PUBACK      : "PUBACK",
        PUBREC      : "PUBREC",
        PUBREL      : "PUBREL",
        PUBCOMP     : "PUBCOMP",
        SUBSCRIBE   : "SUBSCRIBE",
        SUBACK      : "SUBACK",
        UNSUBSCRIBE : "UNSUBSCRIBE",
        UNSUBACK    : "UNSUBACK",
        PINGREQ     : "PINGREQ",
        PINGRESP    : "PINGRESP",
        DISCONNECT  : "DISCONNECT",
        _RESERVED2  : "_RESERVED2",
    }

    @staticmethod
    def to_string(ptype):
        return ControlPacketType.__STRINGS.get(ptype, "Unknown? ({0})".format(ptype))

    class PublishFlags:
        def __init__(self, DUP=0, QoS=0, RETAIN=0, from_raw=False):
            """
            DUP    : Duplicate delivery of a PUBLISH Control Packet
            QoS    : PUBLISH Quality of Service
            RETAIN : PUBLISH Retain flag
            """
            super().__init__()
            if from_raw:
                self.dup, self.qos, self.retain = DUP, QoS, RETAIN
            else:
                self.dup    = 0 if QoS == 0 else DUP
                self.qos    = QoS if QoS in WillQoS.CHECK_VALID else 0
                self.retain = RETAIN

        def __str__(self):
            return style("<dup={0}, QoS={1}, ret={2}>" \
                            .format(self.dup, self.qos, self.retain),
                        Colours.FG.CYAN)

        @classmethod
        def from_byte(cls, raw):
            raw = Bits.to_single_byte(raw)
            dup, qos, ret = Bits.get(raw, 4), Bits.get(raw, 1, 2), Bits.get(raw, 0)
            return cls(dup, qos, ret, from_raw=True)

        def to_bin(self):
            return Bits.bit(3, self.dup)    \
                 | Bits.bit(1, self.qos, 2) \
                 | Bits.bit(0, self.retain)


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

    __VALID_FLAGS = {
        _RESERVED1  : -1,
        CONNECT     : Flags.CONNECT,
        CONNACK     : Flags.CONNACK,
        PUBLISH     : Flags.PUBLISH,
        PUBACK      : Flags.PUBACK,
        PUBREC      : Flags.PUBREC,
        PUBREL      : Flags.PUBREL,
        PUBCOMP     : Flags.PUBCOMP,
        SUBSCRIBE   : Flags.SUBSCRIBE,
        SUBACK      : Flags.SUBACK,
        UNSUBSCRIBE : Flags.UNSUBSCRIBE,
        UNSUBACK    : Flags.UNSUBACK,
        PINGREQ     : Flags.PINGREQ,
        PINGRESP    : Flags.PINGRESP,
        DISCONNECT  : Flags.DISCONNECT,
        _RESERVED2  : -1,
    }

    @staticmethod
    def check_flags(ptype, pflag):
        return ControlPacketType.__VALID_FLAGS.get(ptype) == pflag \
            if ptype != ControlPacketType.PUBLISH else True


class WillQoS:
    QoS_0 = 0x0  # At most one delivery
    QoS_1 = 0x1  # At least one delivery
    QoS_2 = 0x2  # Exactly one delivery
    QoS_3 = 0x3  # Reserved – must not be used

    CHECK_VALID = (QoS_0, QoS_1, QoS_2)


class ReturnCode:
    NO_CODE = -1

    ACCEPTED              = 0x00  # Connection accepted
    UNACCEPTABLE_PROT_LVL = 0x01  # Conn refused, unacceptable protocol level
    ID_REJECTED           = 0x02  # Conn refused, identifier rejected
    SERVICE_UNAVAILABLE   = 0x03  # Conn refused, server unavailable
    BAD_AUTH              = 0x04  # Conn refused, bad user name or password
    NOT_AUTHORISED        = 0x05  # Conn refused, not authorized

class SUBACKReturnCode:
    SUCCESS_MAX_QoS_0 = 0x00  # Success - Maximum QoS 0
    SUCCESS_MAX_QoS_1 = 0x01  # Success - Maximum QoS 1
    SUCCESS_MAX_QoS_2 = 0x02  # Success - Maximum QoS 2
    FAILURE           = 0x80  # Failure

    CHECK_VALID = (SUCCESS_MAX_QoS_0, SUCCESS_MAX_QoS_1, SUCCESS_MAX_QoS_2)
