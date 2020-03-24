import bluetooth

# https://github.com/eclipse/paho.mqtt.python
import paho.mqtt.client as MQTT
from paho.mqtt.client import MQTTv311

from os import path
import traceback

from BLE2MQTT.bits import Bits
from BLE2MQTT.colours import *


class BLE2MQTT:
    def __init__(self, name, addr):
        self.ble_name   = name
        self.addr       = addr
        self.topic_base = "-".join(self.ble_name.split(' '))

        self.mqtt = MQTT.Client(client_id=self.name(), clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")
        self.mqtt.will_set(self.topic("connected"), payload=b"false", qos=0, retain=True)

        self.ble_connected  = False
        self.mqtt_connected = False

        self.ble_sock = None

    def __del__(self):
        if self.mqtt_connected:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

    def _log(self, msg):
        print("{0} {1}".format(self, msg))

    def _logble(self, msg):
        self._log("[{0}] {1}".format(style("BLE", Colours.FG.CYAN), msg))

    def _logmqtt(self, msg):
        self._log("[{0}] {1}".format(style("MQTT", Colours.FG.BLUE), msg))

    def _error(self, e=None):
        if e:
            self._log(style(type(e).__name__, Colours.FG.RED) + ": {}".format(e))
            self._log(style(traceback.format_exc(), Colours.FG.BRIGHT_MAGENTA))
        else:
            self._log(style("Unknown error", Colours.FG.RED))

    def __str__(self):
        return style("{0}".format(self.name()), Colours.FG.YELLOW)

    def __repr__(self):
        return style("<{0}, ble={1}, mqtt={2}>".format(self.name(), self.ble_connected, self.mqtt_connected), Colours.FG.YELLOW)

    def topic(self, name):
        return path.join(self.topic_base, name)

    def name(self):
        return self.topic_base

    @classmethod
    def from_name(cls, name):
        found_addr = None

        for bdaddr, name in BLE2MQTT.ble_discover():
            if name == name:
                found_addr = bdaddr
                break

        if found_addr is not None:
            print("Found device '{0}' with address: {1}".format(name, found_addr))
        else:
            raise Exception("Could not find device '{0}'!".format(name))

        return cls(name, found_addr)


    ###########################################################################
    ## BLUETOOTH

    @staticmethod
    def ble_discover():
        return bluetooth.discover_devices(lookup_names=True)

    def ble_connect(self):
        # TODO implement me

        service_matches = bluetooth.find_service(name=None, uuid=None, address=self.addr)
        first_match = service_matches[0]
        self._logble("Uses protocol: " + first_match["protocol"])

        try:
            self.ble_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)

            self._logble("Attempting connect...")
            self.ble_sock.connect((self.addr, 3))
        except Exception as e:
            self._error(e)
            self.ble_connected = False
        else:
            self._logble(style("Connected", Colours.FG.GREEN))
            self.ble_connected = True  # OK

    def ble_get(self):
        # TODO implement me: get next packet?
        # e.g. proper reading and getting length and
        # then only read length amount of bytes left.
        return self.ble_sock.recv(1024)


    ###########################################################################
    ## MQTT

    def _on_connect(self, client, userdata, flags, rc):
        self._logmqtt(style("Connected", Colours.FG.GREEN) \
                    + " with result code {}".format(rc))

        # client.subscribe("$SYS/#")

        # client.message_callback_add(sub, callback)

        self.mqtt_connected = True

    def _on_disconnect(self, client, userdata, rc):
        self._logmqtt(style("Disconnected", Colours.FG.RED) \
                    + "with result code {}".format(rc))

    def _on_message(self, client, userdata, msg):
        self._logmqtt("Received on '{0}' ({1}): {2}".format(
                msg.topic, msg.qos,
                Bits.bytes_to_str(msg.payload)))

    def mqtt_connect(self, host, port=1883, lifetime=60):
        self.mqtt.on_connect    = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect
        self.mqtt.on_message    = self._on_message
        self.mqtt.connect(host, port, lifetime)

    def mqtt_publish(self, topic, payload, qos=0, retain=False):
        topic = self.topic(topic)

        self._logmqtt("Publishing to '{0}': {1}".format(topic, Bits.bytes_to_str(payload)))
        self.mqtt.publish(topic, Bits.str_to_bytes(payload), qos, retain)


    ###########################################################################
    ## General

    def start(self):
        self.mqtt.loop_start()

        while self.ble_connected and self.mqtt_connected:
            # TODO Receive inputs from controller

            ble_pack = self.ble_get()

            # on each button, do:
            self.mqtt_publish("X", Bits.pack(1, 1))


if __name__ == "__main__":
    client = BLE2MQTT.from_name("Xbox Wireless Controller")
    client.ble_connect()
    client.mqtt_connect("127.0.0.1")
    client.start()
