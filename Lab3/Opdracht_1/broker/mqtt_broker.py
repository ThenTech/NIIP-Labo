import socket
import time

try:
    import select
except:
    import uselect as select

DEBUG = True

#############
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


################
# Thread wrapper
try:
    from threading import Thread, Lock, get_ident
    mupy = False
except:
    import _thread
    mupy = True

class Threading:
    @staticmethod
    def new_thread(func, args):
        """
        Create and start a new thread.
        """
        if mupy:
            return _thread.start_new_thread(func, args)
        else:
            tr = Thread(target=func, args=args)
            tr.start()
            return tr

    @staticmethod
    def new_lock():
        """
        Return a Mutex lock object.

        Example:
            lock = Threading.new_lock()
            with lock:
                pass
        """
        if mupy:
            return _thread.allocate_lock()
        else:
            return Lock()

    @staticmethod
    def get_current_id():
        """Get the current thread id"""
        return _thread.get_ident() if mupy else \
               get_ident()



class MQTTPacketException(Exception):
    """General exception."""
    pass

class MQTTDisconnectError(Exception):
    """Exception that should always result in disconnect."""
    def __init__(self, *args, **kwargs):
        self.return_code = kwargs.pop("code", ReturnCode.NO_CODE)
        super().__init__(*args, **kwargs)


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
                self.qos    = QoS if QoS in WillQoS.CHECK_VALID else 1
                self.retain = RETAIN

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

        # Parse length
        self.length, offset = self._get_length_from_bytes(raw[1:])

        # Everything else is payload
        self.payload = raw[offset:]

        if self._includes_packet_identifier():
            self.packet_id = self.payload[0:2]
            self.payload   = self.payload[2:]

    @staticmethod
    def from_bytes(raw, expected_type=None):
        packet_type, packet_flags = MQTTPacket._parse_type(raw)

        packet_adaptor = {
            ControlPacketType.CONNECT: Connect,
            ControlPacketType.PUBLISH: Publish,
            ControlPacketType.PUBACK : MQTTPacket,
            ControlPacketType.PUBREC : MQTTPacket,
            ControlPacketType.PUBREL : MQTTPacket,
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

    def _parse_payload(self):
        # To parse the payload for the Connect packet structure, at least 11 bytes are needed (10+)
        if len(self.payload) < 12:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet (too short)!")

        self.protocol_name_length, self.protocol_name = self._extract_next_field()

        if self.protocol_name_length != 4:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Malformed packet, unexpected protocol length '{0}'!"
                                            .format(self.protocol_name_length))

        if self.protocol_name != MQTTPacket.PROTOCOL_NAME:
            raise MQTTDisconnectError("[MQTTPacket::Connect] Invalid protocol name '{0}'!".format(self.protocol_name))

        self.protocol_level = int(self.payload[0:1])
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

        assert(len(self.payload) == self.length - topic_len - id_len)

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

##########################################################################################
#### Socket

class Retrier:
    """Retry a function until it returns true or the try limit is exceeded."""
    def __init__(self, try_callback, success_callback=None, fail_callback=None, tries=5, delay_ms=50):
        super().__init__()
        self.try_callback     = try_callback
        self.success_callback = success_callback
        self.fail_callback    = fail_callback
        self.triggers         = 0
        self.tries            = tries
        self.delay_ms         = delay_ms

    def attempt(self):
        self.triggers = 0

        while True:
            self.triggers += 1

            try:
                if self.try_callback():
                    if self.success_callback: self.success_callback()
                    return True
                else:
                    if self.triggers > self.tries:
                        # Failed too many times
                        if self.fail_callback: self.fail_callback()
                        return False
                    else:
                        if DEBUG:
                            print("Retry: Wait {0} of {1}...".format(self.triggers, self.tries))
                        time.sleep_ms(self.delay_ms)
            except:
                if self.fail_callback: self.fail_callback()
                return False


def socket_recv(sock, poller=None, buff=4096):
    received_data = b''

    def poll_sock():
        if poller:
            res = poller.poll(1000)
            if res and res[0][1] & select.POLLIN:
                return True
            return False
        else:
            return True

    retry = Retrier(poll_sock, tries=10, delay_ms=500)

    while True:
        if retry.attempt():
            data = sock.recv(buff)
            if data:
                received_data += data
            else:
                break
        else:
            break

    return received_data


def socket_send(sock, data, poller=None):
    if poller:
        res = poller.poll(1000)
        res = res and res[0][1] & select.POLLOUT
    else:
        res = True

    if res:
        sock.send(data)
        return True

    return False

##########################################################################################
#### Server

class ConnectedClient:
    ID_COUNTER = 0

    def __init__(self, sock, addr):
        super().__init__()
        self.sock = sock
        self.addr, self.port = addr

        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLOUT | select.POLLIN)

        self.is_active = True
        self.queued_packets_lock = Threading.new_lock()
        self.queued_packets = []

        # Attributes
        self.id            = b"CLIENT{0}".format(self.ID_COUNTER)
        self.connect_flags = None
        self.keep_alive_s  = 0
        self.will_topic    = b""
        self.will_msg      = b""
        self.username      = b""
        self.password      = b""

        self.ID_COUNTER += 1

    def __del__(self):
        self.disconnect()

    def _log(self, msg):
        if DEBUG:
            print("{0} {1}".format(self, msg))

    def address(self):
        return self.addr, self.port

    def keep_conn(self):
        """Check if connection params should be kept."""
        return self.connect_flags.clean == 0 if self.connect_flags else False

    def reconnect(self, sock, addr):
        self.sock = sock
        self.addr, self.port = addr

        if self.keep_alive_s:
            self.sock.settimeout(self.keep_alive_s * 1.5)  # [MQTT-3.1.2-24]

        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLOUT | select.POLLIN)

        self.is_active = True

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        self.is_active = False

    def set_connection(self, conn):
        if isinstance(conn, Connect):
            self.connect_flags = conn.connect_flags
            self.keep_alive_s  = conn.keep_alive_s
            self.will_topic    = conn.will_topic
            self.will_msg      = conn.will_msg
            self.username      = conn.username
            self.password      = conn.password

            if len(conn.packet_id) > 0:
                self.id = conn.packet_id
            else:
                if self.connect_flags.clean == 0:
                    raise MQTTDisconnectError("{0} [MQTTPacket] No id given, but clean was 0!".format(self),
                                                code=ReturnCode.ID_REJECTED)

            if self.keep_alive_s:
                self.sock.settimeout(self.keep_alive_s * 1.5)  # [MQTT-3.1.2-24]
        else:
            self._log("No conn params?")

    def queue_packet(self, packet):
        with self.queued_packets_lock:
            self.queued_packets.append(packet)

    def send_queued(self):
        if self.is_active:
            unsent = []
            with self.queued_packets_lock:
                for pack in self.queued_packets:
                    if not self.send_packet(pack):
                        unsent.append(pack)
                    else:
                        # Wait for ACK
                        if pack.ptype == ControlPacketType.PUBLISH:
                            if self.connect_flags.will_qos == WillQoS.QoS_1:
                                correct, response = self.expect_response(ControlPacketType.PUBACK)
                                if not correct:
                                    raise MQTTDisconnectError("{0} Got nothing when expecting PUBACK!".format(self))
                            elif self.connect_flags.will_qos == WillQoS.QoS_2:
                                correct, response = self.expect_response(ControlPacketType.PUBREC)
                                if not correct:
                                    raise MQTTDisconnectError("{0} Got nothing when expecting PUBREC!".format(self))
                        # TODO Await other responses that don't need to be handled?
                    time.sleep(0.1)
                self.queued_packets = unsent

        return len(self.queued_packets) == 0

    def recv_data(self):
        if not self.is_active:
            raise MQTTDisconnectError("{0} got disconnected.".format(self))

        data = socket_recv(self.sock, self.poller)

        if data:
            self._log("Received: '{0}'".format(data))
        else:
            self._log("Empty response?")

        return data

    def send_packet(self, pack):
        if not self.is_active:
            self.queue_packet(pack)
            return False
            # raise MQTTDisconnectError("{0} got disconnected.".format(self))

        data  = pack.to_bin()
        retry = Retrier(lambda: socket_send(self.sock, data, self.poller), tries=5, delay_ms=450)

        if retry.attempt():
            return True
        return False

    def expect_response(self, ptype):
        raw = self.recv_data()
        if not raw:
            return False, raw
        else:
            response = MQTTPacket.from_bytes(raw, expected_type=ptype)
            return response.ptype == ptype, response

    def CONNACK(self, code=ReturnCode.ACCEPTED, was_restored=False):
        session_present = 1 if (self.connect_flags.clean == 1 or was_restored) and code == ReturnCode.ACCEPTED else 0

        response = MQTTPacket.create_connack(session_present=session_present,
                                             status_code=code)
        self.send_packet(response)

    def RECV_DISCONNECT(self):
        self.will_msg = b""
        # self.disconnect()

    def get_will_packet(self, duplicated=0):
        if not self.connect_flags.will or not self.will_msg:
            return None

        response = MQTTPacket.create_publish(ControlPacketType.PublishFlags(
                                                 duplicated,
                                                 self.connect_flags.will_qos,
                                                 self.connect_flags.will_ret),
                                             self.will_topic,
                                             self.will_msg)

        return self.will_topic, response

    def __str__(self):
        return "<{0}Client '{1}' at {2}:{3}>".format(
                    "INACTIVE " if self.is_active else "",
                    self.id, self.addr, self.port)


class MQTTBroker:
    HOST     = "10.42.0.252"
    PORT     = 1883
    PORT_SSL = 1883

    def __init__(self, host=HOST, port=PORT, use_ssl=False):
        super().__init__()
        self.host = host
        self.port = self.PORT_SSL if use_ssl else port

        self.client_lock = Threading.new_lock()
        self.clients = {}

        self.topic_lock = Threading.new_lock()
        self.topic_subscriptions = {}  # { topic: [clients] }

        self.server_sock = None
        self._init_socket()

    def __del__(self):
        if self.server_sock:
            self.server_sock.close()

    def _log(self, msg):
        if DEBUG:
            print("[BROKER] {0}".format(msg))

    def _info(self, msg):
        print("[BROKER] {0}".format(msg))

    def _init_socket(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self._info("Created at {0}:{1}".format(self.host, self.port))

    def has_client(self, addr):
        with self.client_lock:
            return addr in self.clients

    def _create_client(self, sock, addr):
        with self.client_lock:
            self.clients[addr] = ConnectedClient(sock, addr)
            return self.clients[addr]

    def _swap_client_with_existing(self, client):
        kill_old, existing_cl = False, None
        address = client.address()

        with self.client_lock:
            for addr, cl in self.clients.items():
                if cl is not client and (addr == address or cl.id == client.id):
                    # Already one with this id/address
                    if cl.is_active:
                        # Error already active, close old
                        kill_old, existing_cl = True, cl
                    else:
                        existing_cl = cl
                    break

        if kill_old:
            self._destroy_client(existing_cl.address())

        if existing_cl:
            existing_cl.reconnect(client.sock, address)
            client.sock = None

            with self.client_lock:
                del self.clients[address]
                self.clients[existing_cl.address()] = existing_cl
            return existing_cl, True

        return client, False

    def _destroy_client(self, addr):
        if not self.has_client(addr):
            return

        self._info("Destroying {0}".format(self.clients[addr]))

        # TODO Send WILL message?
        topic, packet = self.clients[addr].get_will_packet()
        with self.topic_lock:
            if topic in self.topic_subscriptions:
                for client in self.topic_subscriptions[topic]:
                    client.send_packet(packet)

        with self.client_lock:
            self.clients[addr].disconnect()
            if not self.clients[addr].keep_conn():
                del self.clients[addr]

    def _serve_request(self, sock, sock_addr_tuple):
        self._destroy_client(sock_addr_tuple)
        client = self._create_client(sock, sock_addr_tuple)

        self._info("New connection with {0} on port {1}".format(client.addr, client.port))

        try:
            client, conn_restored = self._swap_client_with_existing(client)

            # Always expect CONNECT
            raw = client.recv_data()

            if not raw:
                raise MQTTDisconnectError("{0} No CONNECT received! Disconnecting...".format(client))

            conn = MQTTPacket.from_bytes(raw, expected_type=ControlPacketType.CONNECT)

            if not conn:
                # [MQTT-3.1.0-1]
                pt, pf = MQTTPacket._parse_type(raw)
                raise MQTTDisconnectError("{0} Received packet type '{1}' is not a CONNECT packet!.".format(client, pt))

            if not conn.is_valid_protocol_level():
                # [MQTT-3.1.2-2]
                client.CONNACK(ReturnCode.UNACCEPTABLE_PROT_LVL)
                raise MQTTDisconnectError("{0} Unacceptable CONNECT protocol level.".format(client))

            try:
                client.set_connection(conn)
            except MQTTDisconnectError as e:
                if e.return_code == ReturnCode.ID_REJECTED:
                    client.CONNACK(e.return_code)
                    raise MQTTDisconnectError("{0} Reject CONNECT client id.".format(client))
                else:
                    raise
            finally:
                # Check again now that we have the id
                client, conn_restored2 = self._swap_client_with_existing(client)
                client.CONNACK(ReturnCode.ACCEPTED, was_restored=conn_restored or conn_restored2)

            # Client is now connected
            if client.is_active:
                pass
                # TODO Add logic
                # ...

                """
                while True:
                    # Idle: send queue?
                    retry = Retrier(client.send_queued, tries=5, delay_ms=1000)
                    while not retry.attempt(): pass

                    # For new received packets:
                    if packet.ptype == ControlPacketType.CONNECT:
                        raise MQTTDisconnectError("{0} Protocol vialation: got another CONNECT.".format(client))
                    elif packet.ptype == ControlPacketType.PUBLISH:
                        if packet.pflag.qos not in WillQoS.CHECK_VALID:
                            raise MQTTDisconnectError("{0} Invalid PUBLISH QoS.".format(client))

                        # Respond to PUBLISH
                        if packet.pflag.qos == WillQoS.QoS_0:
                            pass
                        elif packet.pflag.qos == WillQoS.QoS_1:
                            client.send_packet(MQTTPacket.create_puback(packet.id))
                        elif packet.pflag.qos == WillQoS.QoS_2:
                            client.send_packet(MQTTPacket.create_pubrec(packet.id))

                        # Save packet in retained (so it can be sent to future subscribers?)
                        if packet.pflag.retain:
                            self.queue_published_data(packet.topic, packet)

                        # Send new publish packet to all subscribers of this topic
                        with self.topic_lock:
                            qos_stop_sending = {}

                            # TODO proper flags and data
                            for topicname, cl_li in self.topic_subscriptions:
                                if topicname.startswith(packet.topic):
                                    republish = MQTTPacket.create_publish(packet.pflag, topicname, packet.payload)
                                    republish.packet_id = packet.id   # TODO Only when QoS level is 1 or 2.

                                    for cl in cl_li:
                                        # Check QoS
                                        if qos_stop_sending.get(cl.id, False):
                                            continue
                                        elif cl.connect_flags.will_qos in (WillQoS.QoS_0, WillQoS.QoS_2):
                                            qos_stop_sending[cl.id] = True
                                        cl.queue_packet(republish)

                    elif packet.ptype == ControlPacketType.PUBREL
                        if packet.pflag != ControlPacketType.Flags.PUBREL:
                            raise MQTTDisconnectError("{0} Malformed PUBREL packet.".format(client))
                """

        except MQTTPacketException as e:
            self._info("Packet error with {0}: {1}".format(client, e))
        except MQTTDisconnectError as e:
            self._info("Disconnecting {0}: {1}".format(client, e))
        except Exception as e:
            self._info("Unknown error with {0} {1}:{2}".format(client, type(e).__name__, e))
        finally:
            self._destroy_client(sock_addr_tuple)

    def start(self):
        self._info("Starting to listen...")

        while True:
            try:
                (client_socket, address) = self.server_sock.accept()
                self._info("Accept client at {0}...".format(address))
                Threading.new_thread(self._serve_request, (client_socket, address))
            except Exception as e:
                self._info("Socket error: {0}".format(e))
                break


##########################################################################################
#### Client

class MQTTClient:
    pass


##########################################################################################

if __name__ == "__main__":
    broker = MQTTBroker(host="", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host=MQTTBroker.HOST, port=MQTTBroker.PORT)
    broker.start()
