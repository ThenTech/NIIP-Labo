import sys
import time
import socket

from bits import Bits
from colours import *
from opposock import OSocket
from packet import Discover
from threads import Threading

try:
    import traceback
    HAS_TRACE = True
except:
    HAS_TRACE = False


class Client:
    MAX_LENGTH = 254

    ADDRESSES = [
        b"+32499123456",
        b"+32499234561",
        b"+32499345612",
        b"+32499456123",
        b"+32499561234",
        b"+32499612345",
    ]

    RETRANSMISSION_TIMEOUT_S = 30
    INCOMING_TIMEOUT_S       = 10


    def __init__(self, address, interactive=True, message=None):
        super().__init__()
        self.address     = address if isinstance(address, bytes) else Client.ADDRESSES[int(address) % len(Client.ADDRESSES)]
        self.interactive = interactive
        check, msg = self._check_msg(message)

        if not self.interactive and not check:
            raise Exception("[Client] No or invalid message to send?")

        self.message = msg

        self.serversock = None
        self.server_addr, self.server_port = 0, 0

        self.clientsock = None

    ###########################################################################

    def _log(self, msg):
        print(style(f"[Client@{self.address}]", Colours.FG.YELLOW), msg)

    def _error(self, e=None, prefix=""):
        if e:
            self._log(prefix + style(type(e).__name__, Colours.FG.RED) + f": {e}")
            if HAS_TRACE:
                self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
        else:
            self._log(prefix + style("Unknown error", Colours.FG.RED))

    ###########################################################################

    def _check_msg(self, data):
        if not data:
            return False, b''

        data = Bits.str_to_bytes(data)

        if len(data) > Client.MAX_LENGTH:
            return False, b''

        return True, data

    def _setup(self):
        # TODO
        self._log("Setting up client...")

        self._log(f"{OSocket.get_local_address()}")

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

    def start(self):
        # Setup
        self._setup()

        # Threading.new_thread(self._server_thread)



        # Broadcast / flood network to get IPs
        # => only filter here on applayer, e.g. only take even numbers/IPs
        # On network layer, just look for everything



        # Send first message from cmd line if set
        if self.message:
            self.send(self.message)

        # If interactive, loop and ask for new messages
        if self.interactive:
            while True:
                try:
                    msg = input("Enter a new message: ")
                    check, msg = self._check_msg(msg)

                    if check:
                        self.send(Bits.str_to_bytes(msg))
                except (EOFError, KeyboardInterrupt):
                    print("")
                    self._log("Requested exit.")
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
            address = Bits.str_to_bytes(sys.argv[i+1])
            i += 2
        elif sys.argv[i] in ("-i", "--interactive"):
            interactive = True
            i += 1
        elif sys.argv[i] in ("-m", "--message"):
            msg = sys.argv[i+1]
            i += 2

    client = Client(address, interactive, msg)
    client.start()
