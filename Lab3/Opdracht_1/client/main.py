from umqttsimple import MQTTClient
from network import WLAN
import machine
import time

SSID = "niip_bram"
ROUTER_PASSWORD = "12345678"
BROKER = "10.42.0.252"
CLIENT_ID = "PyCom"
USERNAME = "NIIP"
PASSWORD = "NIIP"

def sub_cb(topic, msg):
   print(msg)

wlan = WLAN(mode=WLAN.STA)
wlan.connect(SSID, auth=(WLAN.WPA2, ROUTER_PASSWORD), timeout=5000)

while not wlan.isconnected():
    try:
        machine.idle();
    except:
        print("Trying to connect to WiFi")
print("Connected to WiFi\n")

client = MQTTClient(CLIENT_ID, BROKER,user=USERNAME, password=PASSWORD, port=1883)

client.set_callback(sub_cb)
connected = False
while not connected:
    try:
        client.connect()
        print("Connected to broker")
        connected = True
    except:
        print("Retrying to connect to broker")
        time.sleep(1)

client.subscribe(topic="youraccount/feeds/lights")

while True:
    print("Sending ON")
    client.publish(topic="youraccount/feeds/lights", msg="ON")
    time.sleep(1)
    print("Sending OFF")
    client.publish(topic="youraccount/feeds/lights", msg="OFF")
    client.check_msg()
