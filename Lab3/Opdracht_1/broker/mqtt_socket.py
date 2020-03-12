import time
from mqtt_packet import MQTTPacket

try:
    import select
except:
    import uselect as select


DEBUG = True

##########################################################################################
#### Socket

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
        self.triggers = 0

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
                        if DEBUG:
                            print("Retry: Wait {0} of {1}...".format(self.triggers, self.tries))
                        time.sleep_ms(self.delay_ms)
            except:
                if self.fail_callback: self.fail_callback()
                return False


def socket_recv(sock, poller=None, buff=4096):
    received_data = b''
    variable_length = 0
    got_header = False

    def poll_sock():
        if poller:
            res = poller.poll(1000)
            if res and res[0][1] & select.POLLIN:
                return True
            return False
        else:
            return True

    def get_header():
        data = sock.recv(1)
        len_bytes = b""

        while True:
            bb = sock.recv(1)
            len_bytes += bb

            if (bb[0] & 128) == 0:
                break

        length, _ = MQTTPacket._get_length_from_bytes(len_bytes)
        return data + len_bytes, length

    retry = Retrier(poll_sock, tries=10, delay_ms=500)
    payload = b""

    while True:
        if retry.attempt():
            if not got_header:
                got_header = True
                received_data, variable_length = get_header()
                buff = min(buff, variable_length)
            else:
                if len(payload) < variable_length:
                    data = sock.recv(variable_length - len(payload))

                    if data:
                        payload += data

        if got_header and len(payload) == variable_length:
            break

    return received_data + payload


def socket_send(sock, data, poller=None):
    if poller:
        res = poller.poll(1000)
        res = res and res[0][1] & select.POLLOUT
    else:
        res = True

    if res:
        sock.send(data)
        return True

    return False
