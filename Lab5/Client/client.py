import sys
import time
import random
import socket
import json

from bits import Bits
from colours import *
from opposock import OSocket
from packet import IPacket, PacketType, ContactRelay
from threads import Threading

from client_extra import ClientException, CommunicationType, AddressFilterType, ContactRelayMetadata, MeshMetadata

try:
    import traceback
    HAS_TRACE = True
except:
    HAS_TRACE = False


class Client:
    PORT_BROADCAST_SEND = 10100
    PORT_MESSAGES       = 5000

    MAX_LENGTH = 254

    ADDRESSES = [
        "499123456",
        "499234561",
        "499345612",
        "499456123",
        "499561234",
        "499612345",
    ]

    RETRANSMISSION_TIMEOUT_S = 10
    OPPO_HISTORY_TTL         = 60
    CONTACTS_TTL             = 60


    def __init__(self, address, interactive=True, message=None, address_whitelist=None, filter_addresses=AddressFilterType.ALLOW_ALL):
        super().__init__()
        self.address     = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(address)))
        self.interactive = interactive
        self.message     = msg

        self.serversock = None
        self.server_addr, self.server_port = 0, 0

        self.broadcast_sock = None
        self.contacts_last_update = time.time() + Client.CONTACTS_TTL * 2

        ipbytes = OSocket.get_local_address_bytes()
        ipstr   = OSocket.ip_from_bytes(ipbytes)
        self.ipaddr = (ipstr, ipbytes)

        self.addr_book_lock = Threading.new_lock()
        self.addr_book = {
            self.address: ipstr  # Add self
        }

        self.clientsock = None

        self.id_lock      = Threading.new_lock()
        self.ids_in_use   = set()
        self.last_used_id = 1

        self.expect_acks_lock = Threading.new_lock()
        self.expect_acks = {}   # { pid: packet }

        self.input_newline = Threading.new_lock()

        self.address_whitelist = address_whitelist or []
        self.filter_addresses  = filter_addresses if filter_addresses in AddressFilterType.CHOICES else AddressFilterType.ALLOW_ALL

        self.oppo_metadata_lock = Threading.new_lock()
        self.oppo_metadata = {}  # { (pid, src): ContactRelayMetadata }

        self.mesh_metadata_lock = Threading.new_lock()
        self.mesh_metadata = {}  # { (pid, src): MeshMetadata }


    def __del__(self):
        pass

    ###########################################################################

    def get_address(self):
        """Returns address (tel nr) as number."""
        return self.address

    def get_address_bytes(self):
        """Returns address (tel nr) as bytes."""
        return Bits.pack(self.address, 4)

    def get_ipaddress_bytes(self):
        """Returns IP as 4 bytes."""
        return self.ipaddr[1]

    def get_ipaddress(self):
        """Return IP as dotted string."""
        return self.ipaddr[0]

    def _printnl(self):
        if self.input_newline.locked():
            print("")
            self.input_newline.release()

    def _log(self, msg):
        self._printnl()
        print(style(f"[Client@{self.get_address()}]", Colours.FG.YELLOW), msg)

    def _error(self, e=None, prefix=""):
        self._printnl()
        if e:
            self._log(prefix + style(type(e).__name__, Colours.FG.RED) + f": {e}")
            if HAS_TRACE:
                self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
        else:
            self._log(prefix + style("Unknown error", Colours.FG.RED))

    ###########################################################################

    def next_id(self):
        with self.id_lock:
            if not self.ids_in_use:
                self.last_used_id = 1
                self.ids_in_use.add(1)
                return Bits.pack(1, 1)
            else:
                # Go to next id first, and only reuse lower ones if wrapped back around.
                next_id = self.last_used_id + 1
                if next_id == 0xFF:
                    next_id = 1

                while next_id in self.ids_in_use:
                    next_id += 1

                if next_id > 0xFF:
                    raise ClientException("Largest id reached!")
                else:
                    self.last_used_id = next_id
                    self.ids_in_use.add(next_id)
                    return Bits.pack(next_id, 1)

    def add_incoming_id(self, idx):
         with self.id_lock:
            self.ids_in_use.add(idx)

    def release_id(self, idx):
        with self.id_lock:
            self.ids_in_use.discard(Bits.unpack(idx))

    def add_new_address(self, packet):
        if not isinstance(packet, IPacket):
            return

        with self.addr_book_lock:
            addr, ip = packet.source_addr, OSocket.ip_from_bytes(packet.payload)
            self.addr_book[addr] = ip

            self._log(style("Address book: ", Colours.FG.GREEN) + \
                      style(", ".join(map(str, sorted(self.addr_book.keys()))), Colours.FG.BRIGHT_GREEN))

    def address_exists(self, addr):
        with self.addr_book_lock:
            return addr in self.addr_book

    def address_lookup_ip(self, addr):
        with self.addr_book_lock:
            return self.addr_book.get(addr)

    def add_expected_ack_for(self, packet):
        with self.expect_acks_lock:
            self.expect_acks[packet.pid] = packet

    def check_expected_ack(self, pid):
        with self.expect_acks_lock:
            if pid in self.expect_acks:  # and self.expect_acks[pid].dest_addr == source_addr
                del self.expect_acks[pid]
                return True
            else:
                return False

    def oppo_get_next_hop_for(self, packet):
        with self.addr_book_lock:
            contact_list = set(filter(lambda x: x != self.get_address(), self.addr_book.keys()))

        if not contact_list:
            return -1

        # Create metadata
        meta = ContactRelayMetadata.from_packet(packet)
        key  = meta.get_key()  # (pid, src, dst, is_ack)

        with self.oppo_metadata_lock:
            # If this is an ACK, check if original came through, if so delete it.
            if packet.ptype == PacketType.CONTACT_RELAY_ACK:
                pid, src, dst, is_ack = key
                prev_key = (pid, dst, src, False)

                if prev_key in self.oppo_metadata:
                    self._log(style(f"Removed {self.oppo_metadata[prev_key]} from history due to ACK received!", Colours.FG.BRIGHT_MAGENTA))
                    del self.oppo_metadata[prev_key]

            if key in self.oppo_metadata:
                # Packet metadata already exists
                old_meta = self.oppo_metadata[key]
                next_hop = -1

                # If source is a direct contact, only send back if everything else has been tried.
                knows_source = packet.source_addr in contact_list

                # Find next hop address
                filtered_contacts = contact_list - old_meta.sent_to

                if knows_source:
                    filtered_contacts -= set((packet.source_addr,))

                if filtered_contacts:
                    next_hop = tuple(sorted(filtered_contacts))[0]
                    old_meta.add_sent_to(next_hop)
                elif knows_source:
                    # filtered is empty, but knows source, sent back a final time
                    next_hop = packet.source_addr
                    old_meta.add_sent_to(next_hop)

                if next_hop < 0:
                    # No next hop available, drop packet (or sent back to sender)
                    return -1             # Drop
                    # return meta.prev_hop  # Return to sender?

                old_meta.prev_hop = meta.prev_hop
                meta = old_meta
                self.oppo_metadata[key] = meta
                self._log(style(f"Updated history: {meta}", Colours.FG.BRIGHT_MAGENTA))
            else:
                # Set first contact as next_hop
                if packet.dest_addr in contact_list or packet.dest_addr == self.get_address():
                    # If destination is known, send it there
                    return packet.dest_addr
                elif len(contact_list) == 1:
                    # Only contact is prev_hop or sender
                    if meta.prev_hop != self.get_address() and meta.prev_hop not in contact_list:
                        self._log(style(f"oppo_get_next_hop_for inconsistency: prev hop ({meta.prev_hop}) not in contacts?", Colours.FG.BRIGHT_RED))
                    next_hop = contact_list.pop()
                else:
                    # Get next contact, except prev_hop
                    next_hop = tuple(sorted(contact_list - set((meta.prev_hop,))))[0]

                meta.add_sent_to(next_hop)
                self.oppo_metadata[key] = meta
                self._log(style(f"Added to history: {meta}", Colours.FG.BRIGHT_MAGENTA))

        return meta.next_hop

    def oppo_get_sent_packet(self, pid):
        with self.expect_acks_lock:
            if pid in self.expect_acks:
                return self.expect_acks[pid]
        return None

    def oppo_remove_packet_from_history(self, packet):
        meta = ContactRelayMetadata.from_packet(packet)
        key  = meta.get_key()  # (pid, src, dst, is_ack)

        with self.oppo_metadata_lock:
            if key in self.oppo_metadata:
                self._log(style(f"Removed {self.oppo_metadata[key]} from history due to ACK received.", Colours.FG.BRIGHT_MAGENTA))
                del self.oppo_metadata[key]

    def mesh_add_data(self, pid, dst, data):
        with self.mesh_metadata_lock:
            meta = MeshMetadata(pid, self.get_address(), dst, data)
            self.mesh_metadata[meta.get_key()] = meta

    def mesh_has_data(self, pid, dst):
        key = (pid, self.get_address(), dst)

        with self.mesh_metadata_lock:
            return key in self.mesh_metadata

    def mesh_get_and_remove_data(self, pid, dst):
        key = (pid, self.get_address(), dst)

        with self.mesh_metadata_lock:
            if key in self.mesh_metadata:
                meta = self.mesh_metadata[key]
                del self.mesh_metadata[key]
                return meta.data
        return None


    def _check_msg(self, data):
        if not data:
            return False, b''

        data = Bits.str_to_bytes(data)

        if len(data) > Client.MAX_LENGTH:
            return False, b''

        return True, data

    ###########################################################################

    def _setup_message_server(self):
        self.serversock = OSocket.new_udpserver(("", Client.PORT_MESSAGES))
        Threading.new_thread(self._server_thread)

    def _server_thread(self):
        while True:
            try:
                (raw, addr_tuple) = self.serversock.recvfrom(4096)

                addr, port = addr_tuple
                self._log(f"Incoming connection from {addr}:{port}")

                response = IPacket.from_bytes(raw)

                if not response:
                    continue

                if response.dest_addr == self.get_address():
                    # Messages addressed to self => send ACK or release expected pid.
                    self._log(f"Received: {response}")

                    # Direct Message
                    if response.ptype == PacketType.MESSAGE:
                        self._log(style(f"Incoming message from {response.source_addr}: ", Colours.FG.GREEN) + \
                                  style(f"{Bits.bytes_to_str(response.payload)}", Colours.FG.BRIGHT_GREEN))

                        packet = IPacket.create_message_ack(response.pid,
                                                            self.get_address(),
                                                            response.source_addr)
                        self._log(f"Responding with ACK: {packet}")
                        self.serversock.sendto(packet, (addr, Client.PORT_MESSAGES))
                    elif response.ptype == PacketType.MSGACK:
                        if self.check_expected_ack(response.pid):
                            self.release_id(response.pid)
                            self._log(style("Message was acknowledged!", Colours.FG.GREEN))

                    # Contact Relay message (opportunistic)
                    elif response.ptype == PacketType.CONTACT_RELAY:
                        self._log(style(f"Incoming message from {response.source_addr}: ", Colours.FG.GREEN) + \
                                  style(f"{Bits.bytes_to_str(response.payload)}", Colours.FG.BRIGHT_GREEN))

                        self.oppo_remove_packet_from_history(response)

                        packet = IPacket.create_contact_relay_ack(response.pid,
                                                                  self.get_address(),
                                                                  response.source_addr,
                                                                  -1)

                        next_hop = self.oppo_get_next_hop_for(packet)
                        if next_hop < 0:
                            self._log(style(f"No valid addresses in address book for next hop (for ACK)!", Colours.FG.BRIGHT_RED))
                            continue

                        packet.next_hop = next_hop

                        dest_ip = self.address_lookup_ip(next_hop)
                        if not dest_ip:
                            self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
                            continue

                        self._log(f"Responding with ACK: {packet}")
                        self.serversock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
                    elif response.ptype == PacketType.CONTACT_RELAY_ACK:
                        # Remove sent packet from history
                        sent_packet = self.oppo_get_sent_packet(response.pid)
                        if sent_packet:
                            self.oppo_remove_packet_from_history(sent_packet)
                        elif response.source_addr != self.get_address():
                            self._log(style(f"Ack received for packet we never sent?", Colours.FG.BRIGHT_RED))

                        # Remove pid from expected
                        if self.check_expected_ack(response.pid):
                            self.release_id(response.pid)
                            self._log(style("Message was acknowledged!", Colours.FG.GREEN))

                    # Route Request message (mesh)
                    elif response.ptype == PacketType.ROUTE_REQUEST:
                        self._log(f"Incoming route request from {response.source_addr}")

                        packet = IPacket.create_route_request_ack(response.pid,
                                                                  self.get_address(),
                                                                  response.source_addr,
                                                                  [self.get_address()] + response.get_reverse_route())

                        next_hop = packet.get_next_hop_from(self.get_address())

                        dest_ip = self.address_lookup_ip(next_hop)
                        if not dest_ip:
                            self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
                            continue

                        self._log(f"Responding with ACK: {packet}")
                        self.serversock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
                    elif response.ptype == PacketType.ROUTE_REQUEST_ACK:
                        # Remove pid from expected
                        if self.check_expected_ack(response.pid):
                            self.release_id(response.pid)
                            self._log(style(f"Route request was acknowledged to reach {response.source_addr}: ", Colours.FG.GREEN) + \
                                      style(f"{response.get_reverse_route_string()}", Colours.FG.BRIGHT_GREEN))

                            # Send original message on this route
                            data = self.mesh_get_and_remove_data(response.pid, response.source_addr)

                            if not data:
                                self._log(style(f"The received RouteRequest has no related data to send?", Colours.FG.BRIGHT_RED))
                                continue

                            pid    = self.next_id()
                            packet = IPacket.create_route_relay(pid,
                                                                self.get_address(),
                                                                response.source_addr,
                                                                response.get_reverse_route(),
                                                                data)

                            next_hop = packet.get_next_hop_from(self.get_address())

                            dest_ip = self.address_lookup_ip(next_hop)
                            if not dest_ip:
                                self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
                                continue

                            self._log(f"Sending: {packet}")
                            self.serversock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
                            self.add_expected_ack_for(packet)

                    # Route Relay message (mesh)
                    elif response.ptype == PacketType.ROUTE_RELAY:
                        self._log(style(f"Incoming message from {response.source_addr}: ", Colours.FG.GREEN) + \
                                  style(f"{Bits.bytes_to_str(response.payload)}", Colours.FG.BRIGHT_GREEN))

                        packet = IPacket.create_route_relay_ack(response.pid,
                                                                self.get_address(),
                                                                response.source_addr,
                                                                response.get_reverse_route())

                        next_hop = packet.get_next_hop_from(self.get_address())

                        dest_ip = self.address_lookup_ip(next_hop)
                        if not dest_ip:
                            self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
                            continue

                        self._log(f"Responding with ACK: {packet}")
                        self.serversock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
                    elif response.ptype == PacketType.ROUTE_RELAY_ACK:
                        # Remove pid from expected
                        if self.check_expected_ack(response.pid):
                            self.release_id(response.pid)
                            self._log(style("Route relay message was acknowledged!", Colours.FG.GREEN))
                else:
                    self._log(f"Received: {response}")

                    # Relayed messages, not destined to self => relay further
                    if response.ptype in (PacketType.CONTACT_RELAY, PacketType.CONTACT_RELAY_ACK):
                        next_hop = self.oppo_get_next_hop_for(response)
                        if next_hop < 0:
                            if response.source_addr == self.get_address():
                                self._log(style(f"No valid addresses in address book left for next hop, dropping packet!", Colours.FG.BRIGHT_RED))
                                continue

                            self._log(style(f"No valid addresses in address book for next hop, sending back!", Colours.FG.BRIGHT_RED))
                            next_hop = response.prev_hop

                        response.prev_hop   = self.get_address()
                        response.next_hop   = next_hop
                        response.hop_count += 1

                        if response.hop_count > 255:
                            self._log(style(f"Max hop count exceeded, dropping packet!", Colours.FG.BRIGHT_RED))
                            continue

                        dest_ip = self.address_lookup_ip(next_hop)
                        if not dest_ip:
                            self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
                            continue

                        self._log(f"Relaying packet to {next_hop}...")
                        self.serversock.sendto(response, (dest_ip, Client.PORT_MESSAGES))

                    # Mesh Route Request
                    elif response.ptype == PacketType.ROUTE_REQUEST:
                        response.add_next_hop(self.get_address())
                        used_hops = response.get_route()

                        with self.addr_book_lock:
                            for key in self.addr_book:
                                if key not in used_hops:
                                    dest_ip = self.addr_book[key]
                                    self._log(f"Relaying route request to {key}...")
                                    self.serversock.sendto(response, (dest_ip, Client.PORT_MESSAGES))

                    # Mesh Route Relay
                    elif response.ptype in (PacketType.ROUTE_REQUEST_ACK, PacketType.ROUTE_RELAY, PacketType.ROUTE_RELAY_ACK):
                        next_hop = response.get_next_hop_from(self.get_address())

                        with self.addr_book_lock:
                            if next_hop not in self.addr_book:
                                self._log(style(f"Unknown address for route hop '{next_hop}'?", Colours.FG.BRIGHT_RED))
                                continue
                            dest_ip = self.addr_book[next_hop]
                            self._log(f"Relaying route response to {next_hop}...")
                            self.serversock.sendto(response, (dest_ip, Client.PORT_MESSAGES))

                    else:
                        # Unhandled relay type?
                        self._log(style(f"Unhandled Relay type {PacketType.to_string(response.ptype)}!", Colours.FG.BRIGHT_RED))
            except socket.timeout:
                self._log(f"{self.serversock}: {style('Timeout!', Colours.FG.RED)}")
            except socket.error:
                self._log(f"{self.serversock}: {style('Disconnected!', Colours.FG.RED)}")
            except Exception as e:
                self._error(e, prefix="MsgHandler: ")
                break

    def _join_network(self):
        self._log("Joining network by broadcasting address info...")

        self.broadcast_sock = OSocket.new_broadcastserver(("", Client.PORT_BROADCAST_SEND))

        pack = IPacket.create_discover(self.next_id(), self.get_address(), self.get_ipaddress_bytes())

        self._log(f"Broadcasting {pack}")
        self.broadcast_sock.broadcast(pack, dst_port=Client.PORT_BROADCAST_SEND)

        Threading.new_thread(self._server_handle_broadcast_incoming)

    def _network_refresh_contacts(self):
        if time.time() - self.contacts_last_update <= Client.CONTACTS_TTL:
            return

        pack = IPacket.create_discover(self.next_id(), self.get_address(), self.get_ipaddress_bytes())

        self._log(style("Requesting contact update...", Colours.FG.BRIGHT_MAGENTA))

        with self.addr_book_lock:
            old_book = self.addr_book.copy()
            self.addr_book = { self.get_address(): self.addr_book[self.get_address()] }

        for addr, ip in old_book.items():
            if addr != self.get_address():
                self.broadcast_sock.sendto(pack, (ip, Client.PORT_BROADCAST_SEND))

        time.sleep(2)
        self.contacts_last_update = time.time()
        self._log(style("Contact update complete!", Colours.FG.BRIGHT_MAGENTA))

    def _server_handle_broadcast_incoming(self):
        while True:
            try:
                (raw, addr_tuple) = self.broadcast_sock.recvfrom(4096)
                ip, port = addr_tuple

                if ip == self.get_ipaddress():
                    # Don't answer self
                    continue

                self._log(f"Incoming broadcast from {ip}:{port}...")

                response = IPacket.from_bytes(raw)
                if not response:
                    continue

                self._log(f"Received: {response}")

                # Only parse contacts specified from cmdline param list
                if self.address_whitelist and response.source_addr not in self.address_whitelist:
                    self._log(style(f"Ignoring packet from {response.source_addr}, due to whitelist.", Colours.FG.BRIGHT_RED))
                    continue

                # Apply address/contact filtering on Discovery Ack
                if not AddressFilterType.check_allow_address_communication(self.filter_addresses, self.get_address(), response.source_addr):
                    # Discard packet
                    self._log(style(f"Ignoring knowledge of {response.source_addr}, due to address filter.", Colours.FG.BRIGHT_RED))
                    continue

                ######################################################

                if response.ptype == PacketType.DISCACK:
                    # Quick test for consistency: ip in payload should be the same as socket ip
                    if OSocket.ip_from_bytes(response.payload) != ip:
                        self._log(style(f"Wrong IP address in {PacketType.to_string(response.ptype)} payload?", Colours.FG.BRIGHT_RED))

                elif response.ptype == PacketType.DISCOVER:
                    # Send DISCACK
                    pid = self.next_id()
                    packet = IPacket.create_discover_ack(pid,
                                                            self.get_address(),
                                                            response.source_addr,
                                                            self.get_ipaddress_bytes())
                    self._log(f"Responding with ACK: {packet}")
                    self.broadcast_sock.sendto(packet, (ip, Client.PORT_BROADCAST_SEND))
                    self.release_id(pid)

                # Always add address for new broadcasts
                self.add_new_address(response)
            except (EOFError, KeyboardInterrupt) as e:
                self._log(f"Requested exit from broadcast handler ({style(type(e).__name__, Colours.FG.RED)}).")
                return
            except Exception as e:
                self._error(e, prefix="BroadcastHandler")

    def _transmit_packet(self, dest_ip, packet):
        # Create new UDP socket and send the packet to the destination.
        sock = OSocket.new_upd()
        sock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
        packet.transmit_time = time.time()

    def _handle_retransmit(self):
        while True:
            self._network_refresh_contacts()

            # Check for unACKed packets, and retransmit if timeout reached.
            with self.expect_acks_lock:
                current_time = time.time()
                drop_permanently = []

                for pid, packet in self.expect_acks.items():
                    if current_time - packet.transmit_time > Client.RETRANSMISSION_TIMEOUT_S:
                        # Too long ago, retransmit packet
                        self._log(style(f"Retransmitting packet with id {Bits.unpack(packet.pid)}...", Colours.FG.BRIGHT_MAGENTA))

                        # Direct Delivery
                        if packet.ptype == PacketType.MESSAGE:
                            dest_ip = self.address_lookup_ip(packet.dest_addr)
                            if dest_ip:
                                self._transmit_packet(dest_ip, packet)
                            else:
                                self._log(style(f"Unknown address '{packet.dest_addr}' for retransmit?", Colours.FG.BRIGHT_RED))

                        # Opportunistic Contact Relay
                        elif packet.ptype == PacketType.CONTACT_RELAY:
                            next_hop = self.oppo_get_next_hop_for(packet)
                            if next_hop < 0:
                                # Reset history
                                self.oppo_remove_packet_from_history(packet)
                                next_hop = self.oppo_get_next_hop_for(packet)

                            if next_hop < 0:
                                self._log(style(f"No valid addresses in address book left for retramsmit, dropping packet!", Colours.FG.BRIGHT_RED))
                                drop_permanently.append(pid)
                                continue

                            packet.next_hop = next_hop

                            dest_ip = self.address_lookup_ip(packet.next_hop)
                            if dest_ip:
                                self._transmit_packet(dest_ip, packet)
                            else:
                                self._log(style(f"Unknown address '{next_hop}' for retransmit?", Colours.FG.BRIGHT_RED))

                        # Mesh Route Request or Relay
                        elif packet.ptype in (PacketType.ROUTE_REQUEST, PacketType.ROUTE_RELAY):
                            if packet.ptype == PacketType.ROUTE_RELAY:
                                # If RouteRelay failed, resend a RouteRequest to discover a new route if possible.
                                self.mesh_add_data(packet.pid, packet.dest_addr, packet.payload)
                                packet = IPacket.create_route_request(packet.pid, self.get_address(), packet.dest_addr, [self.get_address()])

                            # Resend RouteRequest to every contact
                            with self.addr_book_lock:
                                for key in self.addr_book:
                                    dest_ip = self.addr_book[key]
                                    self._transmit_packet(dest_ip, packet)

                        else:
                            self._log(style(f"Unknown packet type '{PacketType.to_string(packet.ptype)}' for retransmit?", Colours.FG.BRIGHT_RED))

                for pid in drop_permanently:
                    del self.expect_acks[pid]

            # Check OppoMetadata history and remove entries if TTL reached.
            with self.oppo_metadata_lock:
                current_time = time.time()

                for key in tuple(self.oppo_metadata.keys()):
                    meta = self.oppo_metadata[key]

                    if current_time - meta.last_seen > Client.OPPO_HISTORY_TTL:
                        self._log(style(f"Removed {meta} from history due to TTL reached!", Colours.FG.BRIGHT_MAGENTA))
                        del self.oppo_metadata[key]

            time.sleep(2)


    def start(self):
        self._log(f"Setting up client at {self.get_ipaddress()}...")

        if self.address_whitelist:
            self._log(style(f"Address whitelist (if available; others are ignored): {self.address_whitelist}",
                            Colours.FG.BRIGHT_MAGENTA))
        else:
            self._log(style(f"Address whitelist: All", Colours.FG.BRIGHT_MAGENTA))

        self._log(style(f"Applying filter to broadcasts: {AddressFilterType.to_string(self.filter_addresses)}",
                        Colours.FG.BRIGHT_MAGENTA))

        # Broadcast / flood network to get IPs
        self._join_network()

        # Setup message server
        self._setup_message_server()

        # Wait a bit for broadcasts to complete
        time.sleep(2)

        # Setup retransmit handler
        Threading.new_thread(self._handle_retransmit)

        # Send first message from cmd line if set
        if self.message:
            self._log("Sending initial message from cmd...")
            adr, msg = self.message.split(':', 1)

            try:
                adr, comm_type = adr.rsplit('@', 1)
                comm_type = int(comm_type)
            except:
                comm_type = CommunicationType.DIRECT_ROUTE

            adr = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(adr)))

            check, msg = self._check_msg(msg)
            if check:
                self.send(adr, msg)
            else:
                self._log(style(f"Invalid message! ('{msg}' to {adr})", Colours.FG.RED))

        # If interactive, loop and ask for new messages
        if self.interactive:
            print(style("Enter an address in the form <number>@<communication_type>, " + \
                        f"where communication_type is one of {CommunicationType.CHOICES} " + \
                        f"\n(meaning: {', '.join(map(CommunicationType.to_string, CommunicationType.CHOICES))})",
                        Colours.FG.BRIGHT_YELLOW))

            while True:
                try:
                    self.input_newline.acquire(False)
                    adr = input(style("Enter an address    >", Colours.BG.YELLOW, Colours.FG.BLACK) + " ")
                    if not adr:
                        continue

                    # DEBUG COMMANDS
                    if adr in ("contacts", "book"):
                        # Print address book
                        if self.input_newline.locked():
                            self.input_newline.release()
                        self._log(style("Address book: ", Colours.FG.GREEN) + \
                                  style(", ".join(map(str, sorted(self.addr_book.keys()))), Colours.FG.BRIGHT_GREEN))
                        continue
                    elif adr == "oppometa":
                        # Print Opportunistic ContactRelay metadata
                        with self.oppo_metadata_lock:
                            for val in self.oppo_metadata.values():
                                print(val)
                        continue
                    elif adr == "meshmeta":
                        # Print Mesh RouteRelay metadata
                        with self.mesh_metadata_lock:
                            for val in self.mesh_metadata.values():
                                print(val)
                        continue

                    try:
                        adr, comm_type = adr.rsplit('@', 1)
                        comm_type = int(comm_type)
                    except:
                        comm_type = CommunicationType.DIRECT_ROUTE

                    adr = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(adr)))

                    # DIRECT_ROUTE, OPPORTUNISTIC, MESH
                    if comm_type == CommunicationType.DIRECT_ROUTE:
                        if not self.address_exists(adr):
                            if self.input_newline.locked():
                                self.input_newline.release()
                            self._log(style(f"Unknown address '{adr}'?", Colours.FG.BRIGHT_RED))
                            continue
                    elif comm_type == CommunicationType.OPPORTUNISTIC:
                        pass
                    elif comm_type == CommunicationType.MESH:
                        pass

                    self.input_newline.acquire(False)
                    msg = input(style("Enter a new message >", Colours.BG.YELLOW, Colours.FG.BLACK) + " ")
                    check, msg = self._check_msg(msg)

                    if check:
                        self.send(adr, msg, comm_type)
                    else:
                        self._log(style("Invalid message!", Colours.FG.RED))
                except (EOFError, KeyboardInterrupt) as e:
                    print("")
                    self._log(f"Requested exit from interactive mode ({style(type(e).__name__, Colours.FG.RED)}).")
                    sys.exit()
                    return

    def _send_direct(self, address, data):
        dest_ip = self.address_lookup_ip(address)

        # Direct can only send to known contacts in address book
        if not dest_ip:
            self._log(style(f"Unknown address '{address}'?", Colours.FG.BRIGHT_RED))
            return

        self._log(f"Sending to {address} with {CommunicationType.to_string(CommunicationType.DIRECT_ROUTE)}: {data}")

        pid = self.next_id()
        packet = IPacket.create_message(pid, self.get_address(), address, data)
        self._log(f"Sending: {packet}")
        self._transmit_packet(dest_ip, packet)
        self.add_expected_ack_for(packet)

    def _send_opportunistic(self, address, data):
        self._log(f"Sending to {address} with {CommunicationType.to_string(CommunicationType.OPPORTUNISTIC)}: {data}")

        pid      = self.next_id()
        next_hop = -1
        packet   = IPacket.create_contact_relay(pid, self.get_address(), address, next_hop, data)

        # Get first hop address
        next_hop = self.oppo_get_next_hop_for(packet)
        if next_hop < 0:
            self._log(style(f"No valid addresses in address book for next hop!", Colours.FG.BRIGHT_RED))
            return

        packet.next_hop = next_hop

        dest_ip = self.address_lookup_ip(next_hop)
        if not dest_ip:
            self._log(style(f"Unknown address '{next_hop}'?", Colours.FG.BRIGHT_RED))
            return

        self._log(f"Sending: {packet}")
        self._transmit_packet(dest_ip, packet)
        self.add_expected_ack_for(packet)

    def _send_mesh(self, address, data):
        self._log(f"Sending to {address} with {CommunicationType.to_string(CommunicationType.MESH)}: {data}")

        pid = self.next_id()

        with self.addr_book_lock:
            if address in self.addr_book:
                # Send RouteRelay to contact in address book
                packet = IPacket.create_route_relay(pid,
                                                    self.get_address(),
                                                    address,
                                                    [self.get_address(), address],
                                                    data)
                dest_ip = self.addr_book[address]
                self._log(f"Sending: {packet}")
                self._transmit_packet(dest_ip, packet)
            else:
                # Send RouteRequest to every contact
                packet = IPacket.create_route_request(pid, self.get_address(), address, [self.get_address()])

                self._log(f"Sending: {packet}")
                self.mesh_add_data(pid, address, data)

                for key in self.addr_book:
                    if key == self.get_address():
                        continue
                    dest_ip = self.addr_book[key]
                    self._log(f"Sending route request to {key}...")
                    self._transmit_packet(dest_ip, packet)

            self.add_expected_ack_for(packet)

    def send(self, address, data, comm_type=CommunicationType.DIRECT_ROUTE):
        # DIRECT_ROUTE, OPPORTUNISTIC, MESH
        send_handler = {
            CommunicationType.DIRECT_ROUTE  : self._send_direct,
            CommunicationType.OPPORTUNISTIC : self._send_opportunistic,
            CommunicationType.MESH          : self._send_mesh,
        }

        send_handler.get(comm_type, self._send_direct)(address, data)


if __name__ == "__main__":
    address, interactive, msg = 0, True, None
    include_these_addresses_only = []
    filter_type = AddressFilterType.ALLOW_ALL

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("-a", "--address"):
            # Self address (as number in string)
            address = Bits.bytes_to_str(sys.argv[i+1])
            i += 2
        elif sys.argv[i] in ("-i", "--interactive"):
            # Whether to go into interactive mode to send new messages
            interactive = True
            i += 1
        elif sys.argv[i] in ("-m", "--message"):
            # Send an initial message in format: `address[@<comm_type>]:msg`
            msg = sys.argv[i+1]
            i += 2

            if msg == "None":
                msg = None
        elif sys.argv[i] in ("-w", "--whitelist"):
            # A whitelist for incoming addresses (broadcasts)
            json_array = sys.argv[i+1]

            if json_array == "None":
                include_these_addresses_only = None
            else:
                try:
                    json_array = json.loads(sys.argv[i+1])
                except:
                    json_array = []
                finally:
                    include_these_addresses_only = json_array
            i += 2
        elif sys.argv[i] in ("-f", "--filter"):
            # Filter incoming packets
            # == 1: Allow all (default)
            # == 2: Only opposite evenness (e.g. address 1 can only get/sent to even addresses)
            filter_type = sys.argv[i+1]
            i += 2

            filter_type = None if filter_type == "None" else int(filter_type)

    print("Waiting for keypress... (set-up tcp dump now if wanted)")
    input()

    client = Client(address, interactive, msg,
                    address_whitelist = include_these_addresses_only,
                    filter_addresses  = filter_type)
    client.start()
