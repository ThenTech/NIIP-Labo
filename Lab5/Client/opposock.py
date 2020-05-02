import socket

from bits import Bits
from colours import *
from packet import IPacket


class Constants:
    LF   = b"\n"
    CRLF = b"\r\n"

class OSocketException(Exception):
    pass


class OSocket:
    def __init__(self, sock=None, shutdwn=False, addr="127.0.0.1", port=0):
        super().__init__()
        self.sock    = sock
        self.shutdwn = shutdwn

        self.addr = addr
        self.port = port

    def __del__(self):
        if self.sock:
            if self.shutdwn:
                self.shutdown()
            self.sock.close()

    def __str__(self):
        return f"{style(f'{self.addr}:{self.port}', Colours.FG.BRIGHT_BLUE)}"

    def set_addr(self, addr, port):
        self.addr, self.port = addr, port

    def shutdown(self):
        try:
            self.sock.shutdown(1)
        except: pass

    @staticmethod
    def get_local_address():
        return socket.gethostbyname(socket.gethostname())

    @staticmethod
    def get_local_address_bytes():
        ip = OSocket.get_local_address()
        ip = map(int, ip.split('.'))
        return Bits.pad_bytes(bytes(ip), 4)

    @staticmethod
    def ip_from_bytes(raw):
        if len(raw) != 4:
            # Error
            return "0.0.0.0"
        return ".".join(map(str, raw))

    def recv(self, buffer=4096):
        data = b""

        try:
            while True:
                d = self.sock.recv(buffer)
                if not d:
                    break

                data += d

                if d.endswith(Constants.CRLF * 2):
                    break
        except Exception as e:
            raise e
        finally:
            return data

    def broadcast(self, msg, dst_port=10100):
        data = b""

        if isinstance(msg, IPacket):
            data = msg.to_bin()
        elif isinstance(msg, bytes):
            data = msg
        else:
            raise OSocketException("[broadcast] Invalid data?")

        self.sock.sendto(data, ('<broadcast>', dst_port))

    def accept(self):
        if hasattr(self.sock, "accept"):
            return self.sock.accept()
        return None

    def recvfrom(self, buffer=4096):
        if hasattr(self.sock, "recvfrom"):
            return self.sock.recvfrom(buffer)
        return None

    def sendto(self, msg, addr_tuple):
        if hasattr(self.sock, "sendto"):
            data = b""
            if isinstance(msg, IPacket):
                data = msg.to_bin()
            elif isinstance(msg, bytes):
                data = msg
            else:
                raise OSocketException("[broadcast] Invalid data?")
            return self.sock.sendto(data, addr_tuple)
        return None

    @classmethod
    def new_upd(cls):
        return cls(socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP))

    @classmethod
    def new_tcp(cls):
        return cls(socket.socket())

    @classmethod
    def new_server(cls, server_tuple, backlog=5):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.bind(server_tuple)
        sock.listen(backlog)
        return cls(sock, shutdwn=True)

    @classmethod
    def new_udpserver(cls, server_tuple, backlog=5):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(server_tuple)
        return cls(sock, shutdwn=True)

    @classmethod
    def new_broadcastserver(cls, server_tuple=("", 10100)):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(server_tuple)
        return cls(sock, shutdwn=True)
