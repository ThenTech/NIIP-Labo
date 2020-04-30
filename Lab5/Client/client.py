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

class Client:
    PORT_BROADCAST_SEND = 10100
    PORT_BROADCAST_RECV = 10104

    MAX_LENGTH = 254

    ADDRESSES = [
        "499123456",
        "499234561",
        "499345612",
        "499456123",
        "499561234",
        "499612345",
    ]

    RETRANSMISSION_TIMEOUT_S = 30
    INCOMING_TIMEOUT_S       = 10


    def __init__(self, address, interactive=True, message=None):
        super().__init__()
        self.address     = Bits.unpack(IPacket.convert_address(Bits.bytes_to_str(address)))
        self.interactive = interactive
        check, msg = self._check_msg(message)

        if not self.interactive and not check:
            raise Exception("[Client] No or invalid message to send?")

        self.message = msg

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

    def _log(self, msg):
        print(style(f"[Client@{self.get_address()}]", Colours.FG.YELLOW), msg)

    def _error(self, e=None, prefix=""):
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

    def _check_msg(self, data):
        if not data:
            return False, b''

        data = Bits.str_to_bytes(data)

        if len(data) > Client.MAX_LENGTH:
            return False, b''

        return True, data

    def _setup(self):
        # TODO
        self._log(f"Setting up client at {self.get_ipaddress()}...")

        self.serversock = OSocket.new_server(("", 5000))

    ###########################################################################

    def _server_handle_incoming(self, sock, sock_addr_tuple):
        addr, port = sock_addr_tuple
        sock.settimeout(Client.INCOMING_TIMEOUT_S)
        sock = OSocket(sock, addr=addr, port=port)

        self._log(f"New connection with {addr}:{port}")

        # TODO
        try:
            data = sock.recv()
            self._log(f"{sock} received: {data}")

            # TODO: Sent ACK

        except socket.timeout:
            self._log(f"{sock}: {style('Timeout!', Colours.FG.RED)}")
        except socket.error:
            self._log(f"{sock}: {style('Disconnected!', Colours.FG.RED)}")
        except Exception as e:
            self._error(e, prefix=f"{sock}: ")
        finally:
            del sock
            self._log(f"{style(f'{addr}:{port}', Colours.FG.BRIGHT_BLUE)}")


    def _server_thread(self):
        while True:
            try:
                sock_addr_tuple = self.serversock.accept()
                Threading.new_thread(self._server_handle_incoming, sock_addr_tuple)
            except Exception as e:
                self._error(e)
                break

    def _join_network(self):
        self._log("Joining network by broadcasting address info...")

        sock = OSocket.new_broadcastserver(("", Client.PORT_BROADCAST_SEND))
        pack = IPacket.create_discover(self.next_id(), self.get_address(), self.get_ipaddress_bytes())

        self._log(f"Broadcasting {pack}...")
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


    def start(self):
        # Setup
        self._setup()

        # Threading.new_thread(self._server_thread)



        # Broadcast / flood network to get IPs
        self._join_network()
        # => only filter here on applayer, e.g. only take even numbers/IPs
        # On network layer, just look for everything



        # Send first message from cmd line if set
        if self.message:
            self.send(self.message)

        # If interactive, loop and ask for new messages
        if self.interactive:
            while True:
                try:
                    msg = ""  # input("Enter a new message: ")
                    check, msg = self._check_msg(msg)

                    if check:
                        self.send(Bits.str_to_bytes(msg))
                except (EOFError, KeyboardInterrupt) as e:
                    print("")
                    self._log(f"Requested exit from interactive mode ({style(type(e).__name__, Colours.FG.RED)}).")
                    sys.exit()
                    return

    def send(self, data):
        # TODO
        self._log(f"Sending: {data}")

        # if not received_confirmation within RETRANSMISSION_TIMEOUT_S:
        #    self.send(data)

        # TODO Make 2 threads, for sending and receiving, both with udp socket?
        # On send, queue message to send thread
        # On receive display, and send confirm
        #   Only display msgs targeted to self.address, add additional filter to sometimes drop others


if __name__ == "__main__":
    address, interactive, msg = 0, True, None

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("-a", "--address"):
            address = Bits.bytes_to_str(sys.argv[i+1])
            i += 2
        elif sys.argv[i] in ("-i", "--interactive"):
            interactive = True
            i += 1
        elif sys.argv[i] in ("-m", "--message"):
            msg = sys.argv[i+1]
            i += 2

    client = Client(address, interactive, msg)
    client.start()
