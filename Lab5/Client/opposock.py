import socket

from colours import *

class Constants:
    LF   = b"\n"
    CRLF = b"\r\n"


class OSocket:
    def __init__(self, sock=None, cleanup=None, addr="127.0.0.1", port=0):
        super().__init__()
        self.sock    = sock
        self.cleanup = cleanup

        self.addr = addr
        self.port = port

    def __del__(self):
        if self.sock:
            if self.cleanup:
                self.cleanup(self)
            self.sock.close()

    def __str__(self):
        return f"{style(f'{self.addr}:{self.port}', Colours.FG.BRIGHT_BLUE)}"

    def set_addr(self, addr, port):
        self.addr, self.port, addr, port

    @staticmethod
    def get_local_address():
        return socket.gethostbyname(socket.gethostname())

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
    def broadcast(self, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            msg = msg.encode()
        except:
            pass

        host = ''
        port = 10100
        sock.bind((host,port))
        sock.sendto(msg, ('<broadcast>', 10100))

        return sock
    

    def accept(self):
        if hasattr(self.sock, "accept"):
            yield self.sock.accept()
        return None

    @classmethod
    def new_upd(cls):
        return cls(socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP))

    @classmethod
    def new_tcp(cls):
        return cls(socket.socket())

    @classmethod
    def new_server(cls, server_tuple, backlog=5):
        def shutdown(self):
            try:
                self.sock.shutdown(1)
            except: pass

        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.bind(server_tuple)
        sock.listen(backlog)
        return cls(sock, cleanup=shutdown)
