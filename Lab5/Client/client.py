import sys
import time
import random
import socket

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


class ClientException(Exception):
    pass


class SendPacket:
    def __init__(self, packet, dst_ip):
        self.packet = packet
        self.transmit_time = 0
        self.dst_ip = dst_ip

    def update_time(self):
        self.transmit_time = time.time()

    def transmit(self):
        sock = OSocket.new_upd()
        sock.sendto(self.packet, (self.dst_ip, Client.PORT_MESSAGES))
        self.update_time()


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


    def __init__(self, address, interactive=True, message=None):
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

            self._log("Address book: " + ", ".join(map(str, self.addr_book.keys())))

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
                self._log(f"Incoming connection with {addr}:{port}")

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

    def _handle_retransmit(self):
        while True:
            with self.expect_acks_lock:
                current_time = time.time()

                for pid, sent in self.expect_acks.items():
                    if current_time - sent.transmit_time > Client.RETRANSMISSION_TIMEOUT_S:
                        # Too long ago, retransmit packet
                        self._log(style(f"Retransmitting packet with id {Bits.unpack(sent.packet.pid)}...", Colours.FG.BRIGHT_MAGENTA))
                        sent.transmit()

            time.sleep(2)


    def start(self):
        self._log(f"Setting up client at {self.get_ipaddress()}...")

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
            adr = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(adr)))

            check, msg = self._check_msg(message)
            if check:
                self.send(adr, msg)
            else:
                self._log(style(f"Invalid message! ('{msg}' to {adr})", Colours.FG.RED))

        # If interactive, loop and ask for new messages
        if self.interactive:
            while True:
                try:
                    self.input_newline.acquire(False)
                    adr = input(style("Enter an adddress   >", Colours.BG.YELLOW, Colours.FG.BLACK) + " ")
                    adr = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(adr)))

                    if not self.address_exists(adr):
                        self.input_newline.release()
                        self._log(style(f"Unknown address '{adr}'?", Colours.FG.BRIGHT_RED))
                        continue

                    self.input_newline.acquire(False)
                    msg = input(style("Enter a new message >", Colours.BG.YELLOW, Colours.FG.BLACK) + " ")
                    check, msg = self._check_msg(msg)

                    if check:
                        self.send(adr, msg)
                    else:
                        self._log(style("Invalid message!", Colours.FG.RED))
                except (EOFError, KeyboardInterrupt) as e:
                    print("")
                    self._log(f"Requested exit from interactive mode ({style(type(e).__name__, Colours.FG.RED)}).")
                    sys.exit()
                    return

    def send(self, address, data):
        dest_ip = self.address_lookup_ip(address)

        if not dest_ip:
            self._log(style(f"Unknown address '{address}'?", Colours.FG.BRIGHT_RED))
            return

        self._log(f"Sending to {address}: {data}")

        pid = self.next_id()
        packet = IPacket.create_message(pid, self.get_address(), address, data)
        self._log(f"Sending: {packet}")

        transmitpack = SendPacket(packet, dest_ip)
        transmitpack.transmit()
        self.add_expected_ack(pid, transmitpack)


if __name__ == "__main__":
    address, interactive, msg = 0, True, None

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
            # Send an initial message in format: `address:msg`
            msg = sys.argv[i+1]
            i += 2

    client = Client(address, interactive, msg)
    client.start()
