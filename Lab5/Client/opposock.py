from contextlib import contextmanager
import socket


class Constants:
    LF   = b"\n"
    CRLF = b"\r\n"


class OSocket:
    def __init__(self):
        super().__init__()
        self.sock = None

    def __del__(self):
        if self.sock:
            try:
                self.sock.shutdown(1)
            except: pass
            self.sock.close()

    def recv(self, buffer=4096):
        data = []

        try:
            while True:
                d = self.sock.recv(buffer)
                if not d:
                    break

                data.append(d)

                if d.endswith(Constants.CRLF * 2):
                    break
        except Exception as e:
            raise e
        finally:
            return data

    @classmethod
    def new_upd(cls):
        instance = cls()
        instance.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        return instance

    @classmethod
    def new_tcp(cls):
        instance = cls()
        instance.sock = socket.socket()
        return instance

    @classmethod
    def new_server(cls, server_tuple, backlog=1):
        instance = cls()
        instance.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        instance.sock.bind(server_tuple)
        instance.sock.listen(backlog)
        return instance
