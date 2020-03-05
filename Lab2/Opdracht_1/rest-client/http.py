
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


class ReceivedHttpResponse:
    """ Parse Http response messages."""

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
    # METHOD       = b"POST"
    HTTP_VERSION = b"HTTP/1.1"

    CONTENT_TYPE = b"Content-Type"
    CONTENT_JSON = b"application/json"

    def __init__(self, endpoint):
        super().__init__()

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

        req = [ self.METHOD + b" " + self.endpoint + b" " + self.HTTP_VERSION ]
        req.extend(b"{0:s}: {1:s}".format(k, v) for k, v in self.header.items())

        return Constants.CRLF.join(req) + Constants.CRLF * 2 + self.data

class PostRequest(Request):
    METHOD = b"POST"

    def __init__(self, endpoint):
        super().__init__(endpoint)

class GetRequest(Request):
    METHOD = b"GET"

    def __init__(self, endpoint):
        super().__init__(endpoint)
