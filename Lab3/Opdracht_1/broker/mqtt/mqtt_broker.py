import socket
import time
from mqtt.bits import Bits
from mqtt.colours import *
from mqtt.mqtt_threading import Threading
from mqtt.mqtt_exceptions import *
from mqtt.mqtt_packet_types import *
from mqtt.mqtt_packet import *
from mqtt.mqtt_socket import *
from mqtt.mqtt_subscription import TopicSubscription

try:
    import select
except:
    print("Wrong select")
    import uselect as select

try:
    import traceback
    HAS_TRACE = True
except:
    HAS_TRACE = False

DEBUG = True


##########################################################################################
#### Server

class ConnectedClient:
    LIFETIME_MOD = 1.5
    ID_COUNTER = 0

    def __init__(self, sock, addr):
        super().__init__()
        self.sock = sock
        self.addr, self.port = addr

        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLOUT | select.POLLIN)

        self.is_active = True
        self.queued_packets_lock  = Threading.new_lock()
        self.queued_packets       = []  # [ MQTTPacket() ]
        self.awaited_packets_lock = Threading.new_lock()
        self.awaited_packets      = []  # [ (ptype, sent_apcket)... ]

        self.subscription_lock = Threading.new_lock()
        self.subscribed_topics = {}  # { topic: TopicSubscription() }

        # Attributes
        self.id            = bytes("CLIENT{0}".format(ConnectedClient.ID_COUNTER), "utf-8")
        self.connect_flags = None
        self.keep_alive_s  = 0
        self.will_topic    = b""
        self.will_msg      = b""
        self.username      = b""
        self.password      = b""

        self.start_timestamp = time.time()
        ConnectedClient.ID_COUNTER += 1

    def __del__(self):
        self.disconnect()

    def _log(self, msg):
        if DEBUG:
            print("{0} {1}".format(self, msg))

    def address(self):
        return self.addr, self.port

    def reset_lifetime(self):
        self.start_timestamp = time.time()

    def is_lifetime_exceeded(self):
        # [MQTT-3.1.2-24] After 1.5 * keep_alive, disconnect
        return (time.time() - self.start_timestamp) > self.keep_alive_s * self.LIFETIME_MOD \
            if self.keep_alive_s and self.keep_alive_s > 0 else False

    def keep_conn(self):
        """Check if connection params should be kept."""
        return self.connect_flags.clean == 0 if self.connect_flags else False

    def reconnect(self, sock, addr):
        self.sock = sock
        self.addr, self.port = addr

        if self.keep_alive_s > 0:
            self.sock.settimeout(self.keep_alive_s)

        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLOUT | select.POLLIN)

        self.reset_lifetime()
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
                self._log("renamed to '{0}'".format(str(conn.packet_id, "utf-8")))
                self.id = conn.packet_id
            else:
                if self.connect_flags.clean == 0:
                    raise MQTTDisconnectError("{0} [MQTTPacket] No id given, but clean was 0!".format(self),
                                              code=ReturnCode.ID_REJECTED)

            if self.keep_alive_s > 0:
                self.sock.settimeout(self.keep_alive_s)

            self.reset_lifetime()
            self.is_active = True
        else:
            self._log("No conn params?")

    ###########################################################################
    # Packet backlog related

    def has_queued_packets(self):
        with self.queued_packets_lock:
            return len(self.queued_packets) > 0

    def queue_packet(self, packet, for_sub=None):
        with self.queued_packets_lock:
            if for_sub:
                # TODO Add packet to for_sub to comply with QoS
                # (i.e. don't queue packet more than once if dissalowed)
                pass
            self.queued_packets.append(packet)

    def has_awaited_packets(self):
        with self.awaited_packets_lock:
            return len(self.awaited_packets) > 0

    def await_packet(self, packet):
        with self.awaited_packets_lock:
            self.awaited_packets.append(packet)

    def _get_response(self, ptype, sent_packet):
        """For PUBLISH response exchange to check id"""
        correct, response = self.expect_response(ptype)
        if not correct:
            raise MQTTDisconnectError("{0} Got nothing when expecting {1}!"
                                        .format(self, ControlPacketType.to_string(ptype)))
        elif response.packet_id != sent_packet.packet_id:
            raise MQTTDisconnectError("{0} Got {1} with wrong id! ({2}, expected {3})" \
                                        .format(self, ControlPacketType.to_string(ptype),
                                                response.packet_id, sent_packet.packet_id))
        else:
            self._log("Got {0}".format(response))
            return True
        return False

    def _handle_publish_sent(self, sent_packet):
        """For PUBLISH response exchange"""

        # TODO Queue ACKs and await responses on next iteraton?

        if sent_packet.pflag.qos == WillQoS.QoS_0:
            # Do nothing
            return
        elif sent_packet.pflag.qos == WillQoS.QoS_1:
            self.await_packet((ControlPacketType.PUBACK, sent_packet))
            # self._get_response(ControlPacketType.PUBACK, sent_packet)
        elif sent_packet.pflag.qos == WillQoS.QoS_2:
            self.await_packet((ControlPacketType.PUBREC, sent_packet))
            # if self._get_response(ControlPacketType.PUBREC, sent_packet):
            #     self.send_packet(MQTTPacket.create_pubrel(sent_packet.packet_id))
            #     self._get_response(ControlPacketType.PUBCOMP, sent_packet)

    def handle_publish_recv(self, recv_packet):
        # TODO Queue ACKs and await responses on next iteraton?

        if recv_packet.pflag.qos == WillQoS.QoS_0:
            # Do nothing
            return
        elif recv_packet.pflag.qos == WillQoS.QoS_1:
            self.send_packet(MQTTPacket.create_puback(recv_packet.packet_id))
        elif recv_packet.pflag.qos == WillQoS.QoS_2:
            self.send_packet(MQTTPacket.create_pubrec(recv_packet.packet_id))
            if self._get_response(ControlPacketType.PUBREL, recv_packet):
                self.send_packet(MQTTPacket.create_pubcomp(recv_packet.packet_id))

    def recv_awaited(self):
        """Wait for ACKs that were not yet received."""
        # [MQTT-4.4.0-1]

        with self.awaited_packets_lock:
            if not self.awaited_packets:
                return

            unrecv = []

            for ptype, spack in self.awaited_packets:
                if ptype == ControlPacketType.PUBACK:
                    if self._get_response(ptype, spack):
                        pass  # OK
                    else:
                        self.queue_packet(spack)  # Resend PUBLISH
                elif ptype == ControlPacketType.PUBREC:
                    if self._get_response(ptype, spack):
                        # OK, send next
                        self.queue_packet(MQTTPacket.create_pubrel(spack.packet_id))
                        unrecv.append((ControlPacketType.PUBREC, sent_packet))
                    else:
                        self.queue_packet(spack)  # Resend PUBLISH
                else:
                    unrecv.append((ptype, spack))

            self.awaited_packets = unrecv


    def send_queued(self):
        if self.is_active:
            unsent = []
            with self.queued_packets_lock:
                if not self.queued_packets:
                    return True

                self._log("Sending {0} queued packages...".format(len(self.queued_packets)))

                for pack in self.queued_packets:
                    if not self.send_packet(pack):
                        self._log("Unable to sent {0}, requeueing...".format(pack))
                        unsent.append(pack)
                    else:
                        # Wait for ACK
                        if pack.ptype == ControlPacketType.PUBLISH:
                            self._handle_publish_sent(pack)
                        # TODO Await other responses that don't need to be handled?
                    time.sleep(0.1)
                self.queued_packets = unsent

        return len(self.queued_packets) == 0

    def show_queued(self):
        with self.queued_packets_lock:
            self._log("Queued ({0}){1}".format(
                        len(self.queued_packets),
                        "" if len(self.queued_packets) == 0 else \
                        ": [" + ", ".join(map(str, self.queued_packets)) + "]"
                      ))


    ###########################################################################
    # Subscription related

    def is_subscribed_to(self, topic):
        """Return list of all subscriptions that match."""
        subs = []
        with self.subscription_lock:
            for top, sub in self.subscribed_topics.items():
                if sub.matches(topic):
                    subs.append(sub)
        return subs

    def subscribe_to(self, subscription):
        if not isinstance(subscription, TopicSubscription):
            self._log("WARNING: Subscribing requires TopicSubscription object!")
            return False

        with self.subscription_lock:
            if subscription.topic in self.subscribed_topics:
                # Exact match, update
                self.subscribed_topics[subscription.topic].update_qos(subscription.qos)
            else:
                self.subscribed_topics[subscription.topic] = subscription
        return True

    def unsubscribe_from(self, topic):
        with self.subscription_lock:
            if topic in self.subscribed_topics:
                del self.subscribed_topics[topic]
                return True
        return False

    def show_subscriptions(self):
        with self.subscription_lock:
            self._log("Subscribed to: {0}".format(
                "[" + ", ".join(map(str, self.subscribed_topics.values())) + "]" \
                    if self.subscribed_topics else \
                "None"
            ))

    ###########################################################################
    # Socket related

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
            self.reset_lifetime()
            # self._log("Received: {0}".format(data))
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
            self._log("Sent {0}".format(pack))
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
        session_present = 0

        if ((self.connect_flags and self.connect_flags.clean == 1) or was_restored) \
          and code == ReturnCode.ACCEPTED:
            session_present = 1

        response = MQTTPacket.create_connack(session_present=session_present,
                                             status_code=code)
        self.send_packet(response)

    def RECV_DISCONNECT(self):
        # TODO [MQTT-3.14.4-3] Discard Will message and don't send on explicit DISCONNECT?
        # Is this the way?
        self.will_msg = b""

    def get_will_packet(self, duplicated=0):
        if   not self.connect_flags or (self.connect_flags and not self.connect_flags.will) \
          or not self.will_topic or not self.will_msg:
            return None, None

        response = MQTTPacket.create_publish(ControlPacketType.PublishFlags(
                                                 duplicated,
                                                 self.connect_flags.will_qos,
                                                 self.connect_flags.will_ret),
                                             self.id,  # TODO Wich id in this case?
                                             TopicSubscription.filter_wildcards(self.will_topic),
                                             self.will_msg)

        return self.will_topic, response

    def __str__(self, more=False):
        if more:
            text = "{0}@{1}:{2}{3}".format(
                        str(self.id, "utf-8"), self.addr, self.port,
                        " (INACTIVE)" if not self.is_active else "")
        else:
            text = "{0}{1}".format(
                        str(self.id, "utf-8"),
                        " (INACTIVE)" if not self.is_active else "")

        return style(text, Colours.FG.YELLOW)

    def __repr__(self):
        return "<" + self.__str__(more=True) + ", " \
             + ("Flags: {0}".format(str(self.connect_flags) if self.connect_flags else "None")) \
             + (", KeepAlive: {0}s".format(self.keep_alive_s)) \
             + (", Will: '{0}' => '{1}'".format(str(self.will_topic, "utf-8"), str(self.will_msg, "utf-8")) \
                    if self.connect_flags and self.connect_flags.will else "") \
             + (", Auth: {0}{1}".format(str(self.username, "utf-8"), ':' + str(self.password, "utf-8") if self.password else "") \
                 if self.username else "") \
             + ">"


class MQTTBroker:
    HOST     = "10.42.0.252"
    PORT     = 1883
    PORT_SSL = 1883

    def __init__(self, host=HOST, port=PORT, use_ssl=False, enable_colours=True):
        Colours.FORMAT_ESCAPE_SEQ_SUPPORTED = enable_colours

        super().__init__()
        self.host = host
        self.port = self.PORT_SSL if use_ssl else port

        self.client_lock = Threading.new_lock()
        self.clients = {}

        # self.topic_lock = Threading.new_lock()
        # self.topic_subscriptions = {}

        self.retained_lock = Threading.new_lock()
        self.retained_packets = {}  # { topic: [packets] }

        self.server_sock = None
        self._init_socket()

    def __del__(self):
        if self.server_sock:
            self.server_sock.close()

    def _log(self, msg):
        if DEBUG:
            print(style("[BROKER]", Colours.FG.BRIGHT_BLACK) \
                + " {0}".format(msg))

    def _info(self, msg):
        print(style("[BROKER]", Colours.FG.BRIGHT_WHITE) \
            + " {0}".format(msg))

    def _init_socket(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self._info("Created at {0}:{1}".format(self.host if self.host else "127.0.0.1",
                                               self.port))

    ###########################################################################
    # Sub/Pub related

    def queue_published_data(self, topic, packet):
        with self.retained_lock:
            if topic in self.retained_packets:
                del self.retained_packets[topic]
            elif packet.payload:
                # [MQTT-3.3.1-11]
                self.retained_packets[topic] = packet

    def _publish_to_clients(self, topic, packet):
        qos_stop_sending = {}

        with self.client_lock:
            for client in self.clients.values():
                for sub in client.is_subscribed_to(topic):
                    # TODO Check QoS and do something different?
                    if qos_stop_sending.get(client.id, False):
                        continue
                    elif client.connect_flags.will_qos in (WillQoS.QoS_0, WillQoS.QoS_2):
                        qos_stop_sending[client.id] = True

                    republish = MQTTPacket.create_publish(
                        packet.pflag, packet.packet_id,
                        TopicSubscription.filter_wildcards(topic),
                        packet.payload)
                    client.queue_packet(republish)

    ###########################################################################
    # Client related

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
                        # Error: already active, close old
                        kill_old, existing_cl = True, cl
                    else:
                        existing_cl = cl
                    break

        if kill_old:
            self._log("swap_context: {0} was still active, destroying...".format(existing_cl))
            self._destroy_client(existing_cl.address())

        if existing_cl:
            existing_cl.reconnect(client.sock, address)
            client.sock = None

            with self.client_lock:
                del self.clients[address]
                self.clients[existing_cl.address()] = existing_cl

            self._info("Context restored for {0}".format(existing_cl))
            return existing_cl, True

        return client, False

    def _destroy_client(self, addr):
        if not self.has_client(addr):
            return

        self._info("Destroying {0} ({1} left active)".format(
                   self.clients[addr],
                   len(list(filter(lambda c: c.is_active, self.clients.values()))) - 1))

        # TODO Send WILL message?
        topic, packet = self.clients[addr].get_will_packet()

        if topic and packet:
            self._publish_to_clients(topic, packet)

        with self.client_lock:
            self.clients[addr].disconnect()
            if not self.clients[addr].keep_conn():
                del self.clients[addr]

    def _destroy_all_clients(self):
        if not self.clients:
            return

        with self.client_lock:
            self._info("Destroying {0} clients...".format(len(self.clients)))
            for addr in list(self.clients.keys()):
                self.clients[addr].disconnect()
                del self.clients[addr]

    def _connect_client(self, client):
        client, conn_restored = self._swap_client_with_existing(client)

        # Always expect CONNECT
        raw = client.recv_data()

        if not raw:
            raise MQTTDisconnectError("No CONNECT received!")

        self._info("{0} requested CONNECT.".format(client.__str__(more=True)))

        conn = MQTTPacket.from_bytes(raw, expected_type=ControlPacketType.CONNECT)

        if not conn:
            # [MQTT-3.1.0-1]
            pt, pf = MQTTPacket._parse_type(raw)
            raise MQTTDisconnectError("Received packet type '{0}' is not a CONNECT packet!.".format(pt))

        if not conn.is_valid_protocol_level():
            # [MQTT-3.1.2-2]
            client.CONNACK(ReturnCode.UNACCEPTABLE_PROT_LVL)
            raise MQTTDisconnectError("Unacceptable CONNECT protocol level ({0}).".format(conn.protocol_level))

        try:
            client._log("Received {0}".format(conn))
            client.set_connection(conn)
        except MQTTDisconnectError as e:
            if e.return_code == ReturnCode.ID_REJECTED:
                client.CONNACK(e.return_code)
                raise MQTTDisconnectError("Reject CONNECT client id '{0}'.".format(str(conn.packet_id, "utf-8")))
            else:
                raise
        finally:
            # Check again now that we have the id
            client, conn_restored2 = self._swap_client_with_existing(client)
            client.CONNACK(ReturnCode.ACCEPTED, was_restored=conn_restored or conn_restored2)

        return client

    def _handle_incoming(self, client):
        raw = client.recv_data()

        if not raw:
            raise MQTTDisconnectError("No packet received!")

        is_implemented, err = True, None
        try:
            packet = MQTTPacket.from_bytes(raw)
        except MQTTPacketException as e:
            if "unimplemented" in str(e).lower():
                err = e
            else:
                raise
        finally:
            client._log("Received {0}".format(packet))
            if err:
                raise err

        # Do something with packet
        if packet.ptype == ControlPacketType.CONNECT:
            # CONNECT #########################################################
            raise MQTTDisconnectError("Protocol violation: got another CONNECT!")
        elif packet.ptype == ControlPacketType.PUBLISH:
            # PUBLISH #########################################################
            if packet.pflag.qos not in WillQoS.CHECK_VALID:
                raise MQTTDisconnectError("Invalid PUBLISH QoS ({0})!".format(packet.pflag.qos))

            self._info("PUBLISH to topic '{0}': {1}".format(
                    str(packet.topic, "utf-8"), 
                    "'{0}'".format(str(packet.payload, "utf-8")) if packet.payload else "(no payload)" ))

            # Respond to PUBLISH
            client.handle_publish_recv(packet)

            # Save packet in retained (so it can be sent to future subscribers?)
            # TODO How to remember which client already received these (according to QoS)?
            if packet.pflag.retain:
                self.queue_published_data(packet.topic, packet)

            # Send new publish packet to all subscribers of this topic
            self._publish_to_clients(packet.topic, packet)

        elif packet.ptype == ControlPacketType.PUBREL:
            # PUBREL ##########################################################
            if packet.pflag != ControlPacketType.Flags.PUBREL:
                raise MQTTDisconnectError("Malformed PUBREL packet.")
        elif packet.ptype == ControlPacketType.SUBSCRIBE:
            # SUBSCRIBE #######################################################

            # [MQTT-3.8.4-1] Send SUBACK, with combined return codes and granted QoS (same order as SUBSCRIBE topics)
            # TODO? [MQTT-3.8.4-5] Change max granted QoS? Or give error?
            client.send_packet(MQTTPacket.create_suback(packet.packet_id, packet.topics))

            client._log("is SUBSCRIBING to: {0}".format(", ".join(str(t) for t in packet.topics.values())))

            for topic, sub in packet.topics.items():
                # [MQTT-3.8.4-3] If any topic is already subscribed to, replace with this new subscription (updated QoS)
                client.subscribe_to(sub)

            client.show_subscriptions()

            # Check if any retained packet matches new sub and send it
            with self.retained_lock:
                for topic, ret_pack in self.retained_packets.items():
                    for sub in client.is_subscribed_to(topic):
                        client.queue_packet(ret_pack, for_sub=sub)

        elif packet.ptype == ControlPacketType.UNSUBSCRIBE:
            # UNSUBSCRIBE #####################################################

            client.send_packet(MQTTPacket.create_unsuback(packet.packet_id))

            client._log("is UNSUBSCRIBING from: {0}".format(", ".join(packet.topics)))

            for topic in packet.topics:
                # [MQTT-3.10.4-1] Remove subscription topics from client that match exactly
                client.unsubscribe_from(topic)

            client.show_subscriptions()

        elif packet.ptype == ControlPacketType.PINGREQ:
            # PINGREQ #########################################################

            # [MQTT-3.12.4-1] Send response
            # Lifetime was already extended by receiving this packet.
            client.send_packet(MQTTPacket.create_pingresp())

        elif packet.ptype == ControlPacketType.DISCONNECT:
            # DISCONNECT ######################################################
            client.RECV_DISCONNECT()
            raise MQTTDisconnectError("Requested DISCONNECT.")

        # elif packet.ptype == ControlPacketType.*:
        #   pass
        else:
            self._log("{0} No handler for {1} packet.".format(client, packet.name()))

    def _idle_client(self, client):
        if client.has_queued_packets():
            retry = Retrier(client.send_queued, tries=5, delay_ms=1000)
            while not retry.attempt(): pass
        elif client.is_lifetime_exceeded():
            raise MQTTDisconnectError("{0} Exceeded its lifetime ({1}s)."
                    .format(client, client.keep_alive_s * client.LIFETIME_MOD))
        else:
            time.sleep(1)

    def _serve_request(self, sock, sock_addr_tuple):
        self._destroy_client(sock_addr_tuple)
        client = self._create_client(sock, sock_addr_tuple)

        self._info(style("New connection with {0} on port {1}".format(client.addr, client.port), Colours.FG.GREEN))

        try:
            client = self._connect_client(client)

            # Client is now connected
            self._info("Handling {0}".format(repr(client)))

            while client.is_active:
                # Receive packet from client or idle
                if client.has_data():
                    # Incoming packet
                    self._handle_incoming(client)
                else:
                    self._idle_client(client)
        except MQTTPacketException as e:
            self._info(style("Packet error", Colours.FG.RED) \
                     + " with {0}: {1}".format(client, e))
        except MQTTDisconnectError as e:
            self._info(style("Disconnecting", Colours.FG.BRIGHT_RED) \
                     + " {0}: {1}".format(client, e))
        except Exception as e:
            self._info(style("Unknown error", Colours.FG.RED) \
                     + " with {0} {1}: {2}".format(client, type(e).__name__, e))
            if HAS_TRACE: self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
        finally:
            self._destroy_client(sock_addr_tuple)

    def start(self):
        self._info("Starting to listen...")

        while True:
            try:
                (client_socket, address) = self.server_sock.accept()
                self._info("Accept client at {0}:{1}...".format(*address))
                Threading.new_thread(self._serve_request, (client_socket, address))
            except KeyboardInterrupt:
                print("")
                self._destroy_all_clients()
                self._info("Server stopped.")
                break
            except Exception as e:
                self._info(style("Socket error", Colours.FG.RED) + ": {0}".format(e))
                if HAS_TRACE: self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
                break


##########################################################################################

if __name__ == "__main__":
    broker = MQTTBroker(host="", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host="10.42.0.1", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host=MQTTBroker.HOST, port=MQTTBroker.PORT)
    broker.start()
