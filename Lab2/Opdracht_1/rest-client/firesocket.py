import socket
import ssl
import uselect as select


class AddressInfo:
    def __init__(self, tup):
        super().__init__()
        self.family, self.type, self.proto, self.canonname, self.sockaddr = tup

    @classmethod
    def from_address(cls, host, port):
        return cls(socket.getaddrinfo(host, port)[0])


class FireSocket:
    CRLF = b"\r\n"

    def __init__(self):
        super().__init__()

        self.sock = socket.socket()
        self.sock.setblocking(False)
        self.sock = ssl.wrap_socket(self.sock)

        self.addr = None
        self.poller = None

        self.did_handshake = False  # False for SSL

    def __del__(self):
        self.sock.close()

    def close(self):
        self.sock.close()

    def connect(self, host, port):
        self.addr = AddressInfo.from_address(host, port)

        try:
            self.sock.connect(self.addr.sockaddr)
        except OSError as e:
            if '119' in str(e): # For non-Blocking sockets 119 is EINPROGRESS
                print("In Progress")
            else:
                raise e

        self.poller = select.poll()
        self.poller.register(self.sock, select.POLLOUT | select.POLLIN)

    def send(self, data):
        res = self.poller.poll(1000)
        if res and res[0][1] & select.POLLOUT:
            if not self.did_handshake:
                self.did_handshake = True
                self.sock.do_handshake()

            self.sock.send(data)   # + self.CRLF * 2
            #self.poller.modify(self.sock, select.POLLIN)
            return True

        return False

    def recv(self, buff=4096):
        received_data = b''

        while True:
            res = self.poller.poll(1000)
            if res and res[0][1] & select.POLLIN:
                data = self.sock.recv(buff)
                if data:
                    received_data += data
                else:
                    break
            else:
                break

        #self.poller.modify(self.sock, select.POLLOUT)
        return received_data
