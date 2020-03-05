# NETWORK TEST
import network
from firesocket import FireSocket
wlan = network.WLAN(mode=network.WLAN.STA, power_save=True)
wlan.connect("niip_bram", auth=(network.WLAN.WPA2, "12345678"))
wlan.isconnected()


s = FireSocket()
s.connect("10.42.0.1", 5000)
s.send(b"GET /sensors HTTP/1.1\r\n\r\n")
d = s.recv()

d = b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: 45\r\nServer: Werkzeug/1.0.0 Python/2.7.17\r\nDate: Mon, 02 Mar 2020 11:58:50 GMT\r\n\r\n[{"id": "1234", "ip_address": "192.168.0.1"}]'

header, data = d.split(b"\r\n\r\n")
status, fields = header.split(b"\r\n", 1)
status_http, status_msg = status.split(b' ', 1)
fields = {l.split(b':', 1)[0]: l.split(b':', 1)[1].strip() for l in fields.split(b"\r\n")}


s.send(b'POST /notify HTTP/1.1\r\nContent-Type: application/json\r\n\r\n{"sensor_id":"M2M3MWJmODc3YzI0", "msg": "Hello server?"}')


# FUNCTIONAL TEST
from main import *
s = FireSensor()
# wlan and socket...
data = b""
signature_json = ujson.dumps(s.signature_json)
request = PostRequest(s.REMOTE_ROUTE_SIGNUP)
request.add_header(Request.CONTENT_TYPE, Request.CONTENT_JSON)
request.add_data(signature_json)
request.get_payload()


# ENCRYPTION
import crypto
import machine
import ubinascii

pk = open("cert/private_key_1.pem").read()
ids = ubinascii.b2a_base64(ubinascii.hexlify(machine.unique_id())).strip() + "_niip"
ubinascii.b2a_base64(crypto.generate_rsa_signature(ids, pk))
