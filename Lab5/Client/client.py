import sys
import time

from bits import Bits
from colours import *
from opposock import OSocket


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


    def __init__(self, address, interactive=True, message=None):
        super().__init__()
        self.address     = address if isinstance(address, bytes) else Client.ADDRESSES[int(address) % len(Client.ADDRESSES)]
        self.interactive = interactive
        check, msg = self._chech_msg(message)

        if not self.interactive and not check:
            raise Exception("[Client] No or invalid message to send?")

        self.message = msg

    def _log(self, msg):
        print(style(f"[Client@{self.address}]", Colours.FG.YELLOW), msg)

    def _chech_msg(self, data):
        if not data:
            return False, b''

        data = Bits.str_to_bytes(data)

        if len(data) > Client.MAX_LENGTH:
            return False, b''

        return True, data

    def _setup(self):
        # TODO
        self._log("Setting up client...")

    def start(self):
        # Setup
        self._setup()

        # Send first message from cmd line if set
        if self.message:
            self.send(self.message)

        # If interactive, loop and ask for new messages
        if self.interactive:
            while True:
                try:
                    msg = input("Enter a new message: ")
                    check, msg = self._chech_msg(msg)

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
