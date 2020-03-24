import bluetooth
import paho.mqtt.client as mqtt
from bits import Bits
from os import path

class BLE2MQTT:
    def __init__(self, name, addr):
        self.name = ""
        self.addr = ""
        self.mqtt = mqtt.Client(client_id="", clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")

        self.topic_base = "-".join(name.split(' '))

        self.mqtt.will_set(self.topic("connected"), payload=b"false", qos=0, retain=True)

        self.connected = False

    def __del__(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()

    def topic(self, name):
        return path.join(self.topic_base, name)

    @classmethod
    def from_name(cls, name):
        found_addr = None
        nearby_devices = bluetooth.discover_devices(lookup_names=True)

        for bdaddr, name in nearby_devices:
            if name == name:
                found_addr = bdaddr
                break 

        if found_addr is not None:
            print("Found device '{0}' with address: {1}".format(name, found_addr))
        else:
            print("Could not find device '{0}'!".format(name))

        return cls(name, found_addr)


    ###########################################################################
    ## BLUETOOTH

    def connect_ble(self):
        # TODO implement me

        self.connected = True  # if OK


    ###########################################################################
    ## MQTT

    @staticmethod
    def _on_connect(client, userdata, flags, rc):
        print("Connected with result code {}".format(rc))

        # client.subscribe("$SYS/#")

    @staticmethod
    def on_message(client, userdata, msg):
        print("Recv on '{0}': {1}".format(msg.topic, Bits.bytes_to_str(msg.payload)))

    def connect_mqtt(self, host, port=1883, lifetime=60):
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect(host, port, lifetime)
        
        
    ###########################################################################
    ## General

    def start(self):
        self.mqtt.loop_start()

        while connected:
            # TODO Receive imputs from controller
            # on each button, do:
            self.mqtt.publish(self.topic("X"), b"")


if __name__ == "__main__":
    client = BLE2MQTT.from_name("Xbox Wireless Controller")
    client.start()