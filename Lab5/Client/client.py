import sys
import time
import random
import socket
import json


from bits import Bits
from colours import *
from opposock import OSocket
from packet import IPacket, PacketType
from threads import Threading

try:
    import traceback
    HAS_TRACE = True
except:
    HAS_TRACE = False


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


class ClientException(Exception):
    pass


class Client:
    PORT_BROADCAST_SEND = 10100
    PORT_BROADCAST_RECV = 10104
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
    INCOMING_TIMEOUT_S       = 10


    def __init__(self, address, interactive=True, message=None, address_whitelist=None, filter_addresses=AddressFilterType.ALLOW_ALL):
        super().__init__()
        self.address     = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(address)))
        self.interactive = interactive
        self.message     = msg

        self.serversock = None
        self.server_addr, self.server_port = 0, 0

        ipbytes = OSocket.get_local_address_bytes()
        ipstr   = OSocket.ip_from_bytes(ipbytes)
        self.ipaddr = (ipstr, ipbytes)

        self.addr_book_lock = Threading.new_lock()
        self.addr_book = {
            self.address: ipstr  # Add self
        }

        self.clientsock = None

        self.id_lock    = Threading.new_lock()
        self.ids_in_use = set()

        self.expect_acks_lock = Threading.new_lock()
        self.expect_acks = {}   # { pid: packet }

        self.input_newline = Threading.new_lock()

        self.address_whitelist = address_whitelist or []
        self.filter_addresses  = filter_addresses if filter_addresses in AddressFilterType.CHOICES else AddressFilterType.ALLOW_ALL

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
                self.ids_in_use.add(1)
                return Bits.pack(1, 1)
            else:
                next_id = 1
                while next_id in self.ids_in_use:
                    next_id += 1

                if next_id > 0xFF:
                    raise ClientException("Largest id reached!")
                else:
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

    def add_expected_ack(self, pid, packet):
        with self.expect_acks_lock:
            self.expect_acks[pid] = packet

    def check_expected_ack(self, pid):
        with self.expect_acks_lock:
            if pid in self.expect_acks:  # and self.expect_acks[pid].dest_addr == source_addr
                del self.expect_acks[pid]
                return True
            else:
                return False

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

                if response and response.dest_addr == self.get_address():
                    self._log(f"Received: {response}")

                    if response.ptype == PacketType.MESSAGE:
                        self._log(style(f"Incoming message: ", Colours.FG.GREEN) + \
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
            except socket.timeout:
                self._log(f"{self.serversock}: {style('Timeout!', Colours.FG.RED)}")
            except socket.error:
                self._log(f"{self.serversock}: {style('Disconnected!', Colours.FG.RED)}")
            except Exception as e:
                self._error(e, prefix=f"{self.serversock}: ")
                break

    def _join_network(self):
        self._log("Joining network by broadcasting address info...")

        sock = OSocket.new_broadcastserver(("", Client.PORT_BROADCAST_SEND))
        pack = IPacket.create_discover(self.next_id(), self.get_address(), self.get_ipaddress_bytes())

        self._log(f"Broadcasting {pack}")
        sock.broadcast(pack, dst_port=Client.PORT_BROADCAST_SEND)

        Threading.new_thread(self._server_handle_broadcast_incoming, (sock,))

    def _server_handle_broadcast_incoming(self, sock):
        is_even = lambda a: a % 2 == 0
        addr_evenness = is_even(self.get_address())

        while True:
            try:
                (raw, addr_tuple) = sock.recvfrom(4096)
                ip, port = addr_tuple

                if ip == self.get_ipaddress():
                    # Don't answer self
                    continue

                self._log(f"Incoming broadcast from {ip}:{port}...")

                response = IPacket.from_bytes(raw)
                if response:
                    self._log(f"Received: {response}")

                    # Only parse contacts specified from cmdline param list
                    if self.address_whitelist and response.source_addr not in self.address_whitelist:
                        self._log(style(f"Ignoring packet from {response.source_addr}, due to whitelist.", Colours.FG.BRIGHT_RED))
                        continue

                    # Apply address/contact filtering on Discovery Ack
                    if self.filter_addresses == AddressFilterType.ALLOW_ALL:
                        pass
                    elif self.filter_addresses == AddressFilterType.ONLY_OPPOSITE_EVENNESS:
                        if is_even(response.source_addr) == addr_evenness:
                            # Discard ACKs from same sort
                            self._log(style(f"Ignoring knowledge of {response.source_addr}, due to address filter.", Colours.FG.BRIGHT_RED))
                            continue

                    ######################################################

                    if response.ptype == PacketType.DISCACK:
                        # Quick test for consistency: ip in payload should be the same as socket ip
                        if OSocket.ip_from_bytes(response.payload) != ip:
                            self._log(style("Wrong IP address in DISCACK payload?", Colours.FG.BRIGHT_RED))

                    elif response.ptype == PacketType.DISCOVER:
                        # Send DISCACK
                        pid = self.next_id()
                        packet = IPacket.create_discover_ack(pid,
                                                             self.get_address(),
                                                             response.source_addr,
                                                             self.get_ipaddress_bytes())
                        self._log(f"Responding with ACK: {packet}")
                        sock.sendto(packet, (ip, Client.PORT_BROADCAST_SEND))
                        self.release_id(pid)

                    # Always add address for new broadcasts
                    self.add_new_address(response)
            except (EOFError, KeyboardInterrupt) as e:
                self._log(f"Requested exit from broadcast handler ({style(type(e).__name__, Colours.FG.RED)}).")
                return
            except Exception as e:
                self._error(e)

    def _transmit_packet(self, dest_ip, packet):
        sock = OSocket.new_upd()
        sock.sendto(packet, (dest_ip, Client.PORT_MESSAGES))
        packet.transmit_time = time.time()

    def _handle_retransmit(self):
        while True:
            with self.expect_acks_lock:
                current_time = time.time()

                for pid, packet in self.expect_acks.items():
                    if current_time - packet.transmit_time > Client.RETRANSMISSION_TIMEOUT_S:
                        # Too long ago, retransmit packet
                        self._log(style(f"Retransmitting packet with id {Bits.unpack(packet.pid)}...", Colours.FG.BRIGHT_MAGENTA))
                        dest_ip = self.address_lookup_ip(packet.dest_addr)
                        if dest_ip:
                            self._transmit_packet(dest_ip, packet)
                        else:
                            self._log(style(f"Unknown address '{packet.dest_addr}' for retransmit?", Colours.FG.BRIGHT_RED))

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
        # => only filter here on applayer, e.g. only take even numbers/IPs
        # On network layer, just look for everything

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

            if '@' in adr:
                adr, comm_type = adr.rsplit('@', 1)
            else:
                comm_type = 1

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
        self.add_expected_ack(pid, packet)

    def _send_opportunistic(self, address, data):
        # TODO ...

        self._log(f"Sending to {address} with {CommunicationType.to_string(CommunicationType.OPPORTUNISTIC)}: {data}")

        # ...
        self._log(style("Not implemented!", Colours.FG.RED))

    def _send_mesh(self, address, data):
        # TODO ...

        self._log(f"Sending to {address} with {CommunicationType.to_string(CommunicationType.MESH)}: {data}")

        # ...
        self._log(style("Not implemented!", Colours.FG.RED))

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
            filter_type = sys.argv[i+1]
            i += 2

            filter_type = None if filter_type == "None" else int(filter_type)

    print("Waiting for keypress... (set-up tcp dump now)")
    input()

    client = Client(address, interactive, msg,
                    address_whitelist = include_these_addresses_only,
                    filter_addresses  = filter_type)
    client.start()
