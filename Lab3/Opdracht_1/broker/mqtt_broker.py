import socket
import time
import traceback
from bits import Bits 
from mqtt_threading import Threading
from mqtt_exceptions import *
from mqtt_packet_types import *
from mqtt_packet import *
from mqtt_socket import *

try:
    import select
except:
    import uselect as select

DEBUG = True


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
        self.id            = bytes("CLIENT{0}".format(self.ID_COUNTER), "utf-8")
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

            self.is_active = True
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

    def has_data(self):
        if self.poller:
            res = self.poller.poll(1000)
            if res and res[0][1] & select.POLLIN:
                return True
            return False
        return True  # Warning  No poller available

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
        if not self.connect_flags or (self.connect_flags and not self.connect_flags.will) or not self.will_topic:
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
                    str(self.id, "utf-8"), self.addr, self.port)
                

    def __repr__(self):
        return str(self) + "\n" \
             + ("Flags: {0}".format(str(self.connect_flags) if self.connect_flags else "None")) \
             + (", KeepAlive: {0}s".format(self.keep_alive_s)) \
             + (", Will: '{0}' => '{1}'".format(str(self.will_topic, "utf-8"), str(self.will_msg, "utf-8")) \
                    if self.connect_flags and self.connect_flags.will else "") \
             + (", Auth: {0}{1}".format(str(self.username, "utf-8"), ':' + str(self.password, "utf-8") if self.password else "") \
                 if self.username else "")   


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

        if packet:
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

            self._info("Connect packet received! Parsing...")

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
            #print("Client active? " + client.is_active)

            self._info("Handling {0}".format(repr(client)))

            while client.is_active:
                # TODO Add logic
                # ...
                
                # Receive packet from client
                if client.has_data():
                    # Incoming packet
                    raw = client.recv_data()

                    if not raw:
                        raise MQTTDisconnectError("{0} No packet received! Disconnecting...".format(client))

                    is_implemented, err = True, None
                    try:
                        mqtt_packet = MQTTPacket.from_bytes(raw)
                    except MQTTPacketException as e:
                        err = e
                        is_implemented = "Unimplemented" in str(e)
                    finally:
                        self._info("{0} Recieved {1} packet.".format(client, ControlPacketType.to_string(mqtt_packet.ptype)))
                        print(str(raw))

                        if err:
                            raise err
                else:
                    time.sleep(1)

                """
                
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
            track = traceback.format_exc()
            self._info(track)

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

if __name__ == "__main__":
    broker = MQTTBroker(host="10.42.0.1", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host=MQTTBroker.HOST, port=MQTTBroker.PORT)
    broker.start()
