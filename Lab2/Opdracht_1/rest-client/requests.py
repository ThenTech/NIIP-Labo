import socket
import ssl
import uselect as select
import time

DEBUG = False

class Constants:
    """Constants for parsing/splitting"""
    LF   = b"\n"
    CRLF = b"\r\n"

class HttpResponseException(Exception):
    def __init__(self, response):
        self.message = "Not a valid response: '{0}'".format(response)

    def __repr__(self):
        return "HttpResponseException: " + self.message

    __str__ = __repr__


class Retrier:
    """Retry a function until it returns true or the try limit is exceeded."""
    def __init__(self, try_callback, success_callback=None, fail_callback=None, tries=5, delay_ms=50):
        super().__init__()
        self.try_callback     = try_callback
        self.success_callback = success_callback
        self.fail_callback    = fail_callback
        self.triggers         = 0
        self.tries            = tries
        self.delay_ms         = delay_ms

    def attempt(self):
        while True:
            self.triggers += 1

            try:
                if self.try_callback():
                    if self.success_callback: self.success_callback()
                    return True
                else:
                    if self.triggers > self.tries:
                        # Failed too many times
                        if self.fail_callback: self.fail_callback()
                        return False
                    else:
                        print("Wait {0} of {1}...".format(self.triggers, self.tries))
                        time.sleep_ms(self.delay_ms)
            except:
                if self.fail_callback: self.fail_callback()
                return False


class AddressInfo:
    """Convert URL and port to socket AddressInfo."""
    def __init__(self, tup):
        super().__init__()
        self.family, self.type, self.proto, self.canonname, self.sockaddr = tup

    @classmethod
    def from_address(cls, host, port):
        return cls(socket.getaddrinfo(host, port)[0])


class FireSocket:
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

    def __log(self, msg, force=False):
        if DEBUG or force:
            print("[FireSocket] {0}".format(msg))

    def connect(self, host, port):
        self.addr = AddressInfo.from_address(host, port)

        try:
            self.sock.connect(self.addr.sockaddr)
        except OSError as e:
            if '119' in str(e): # For non-Blocking sockets 119 is EINPROGRESS
                self.__log("Connection in Progress")
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
                time.sleep_ms(50)

            self.sock.send(data)   # + self.CRLF * 2
            #self.poller.modify(self.sock, select.POLLIN)
            return True

        return False

    def recv(self, buff=4096):
        received_data = b''

        def poll_sock():
            res = self.poller.poll(1000)
            if res and res[0][1] & select.POLLIN:
                return True
            return False

        while True:
            if Retrier(poll_sock, tries=10, delay_ms=500).attempt():
                data = self.sock.recv(buff)
                if data:
                    self.__log("Received {0} bytes.".format(len(data)))
                    received_data += data
                else:
                    self.__log("End of data.")
                    break
            else:
                break

        #self.poller.modify(self.sock, select.POLLOUT)
        return received_data


class HttpResponse:
    """Parse Http response messages."""

    def __init__(self, raw_str):
        if   not raw_str \
          or (Constants.CRLF * 2) not in raw_str:
            raise HttpResponseException(raw_str)

        self.raw_response = raw_str
        self.protocol     = ""
        self.status_code  = -1
        self.status_msg   = ""
        self.meta_data    = {}
        self.body         = ""

        self._parse()

    def _parse(self):
        # Split raw data
        data_header, self.body = self.raw_response.split(Constants.CRLF * 2, 1)

        # # Take out the trash
        # self.body = remove_garbage_hex(self.body)[0]
        # self.raw_response = data_header + Constants.CRLF * 2 + self.body

        # Parse metadata
        data_header = data_header.split(Constants.CRLF)

        http_resp = data_header[0].split(b' ')
        if len(http_resp) < 3:
            raise HttpResponseException(repr(http_resp))

        self.protocol = http_resp[0]

        if self.protocol.lower().startswith("http"):
            self.status_code = int(http_resp[1])
            self.status_msg  = b" ".join(http_resp[2:])
        else:
            # Not a HTTP protocol (e.g. FTP)
            self.status_code = 0
            self.status_msg  = b" ".join(http_resp[2:]) + b":" + http_resp[1]

        for line in data_header[1:]:
            hdr, data = line.split(b': ', 1)
            self.meta_data[hdr.strip()] = data.strip()

    def isSuccess(self):
        return self.status_code in [200, 302, 304]

    def hasContentLength(self):
        return b"Content-Length" in self.meta_data

    def getContentLength(self):
        return int(self.meta_data.get(b"Content-Length", 0))

    def getBody(self):
        return self.body

    def getFullResponse(self):
        return self.raw_response

    def __str__(self):
        return "<HttpResponse: Protocol={0}, StatusCode={1}, StatusMsg={2}>"\
                    .format(self.protocol, self.status_code, self.status_msg)

    def __repr__(self):
        longest_key_length = max(len(k) for k in self.meta_data)
        return "{0}{1}{2}".format(self, Constants.CRLF,
                                  Constants.CRLF.join('{1:{0}s}: {2}'.format(longest_key_length, k, v)
                                                            for k, v in sorted(self.meta_data.items())))


class Request:
    HTTP_VERSION = b"HTTP/1.1"

    CONTENT_TYPE = b"Content-Type"
    CONTENT_JSON = b"application/json"

    def __init__(self, endpoint, method="GET"):
        super().__init__()

        self.method   = method
        self.endpoint = endpoint
        self.header   = {}
        self.data     = b""

    def add_header(self, name, value):
        if isinstance(value, int) or isinstance(value, float):
            value = "{0}".format(value)
        elif isinstance(value, bytes):
            value = "{0:s}".format(value)
        self.header[name] = value

    def add_data(self, data):
        self.data += data

    def get_payload(self):
        self.add_header("Content-Length", len(self.data))

        req = [ self.method + b" " + self.endpoint + b" " + self.HTTP_VERSION ]
        req.extend(b"{0:s}: {1:s}".format(k, v) for k, v in self.header.items())

        return Constants.CRLF.join(req) + Constants.CRLF * 2 + self.data


class PostRequest(Request):
    def __init__(self, endpoint):
        super().__init__(endpoint, b"POST")

class GetRequest(Request):
    def __init__(self, endpoint):
        super().__init__(endpoint, b"GET")
