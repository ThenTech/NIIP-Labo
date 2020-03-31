# https://github.com/eclipse/paho.mqtt.python
import paho.mqtt.client as MQTT
from paho.mqtt.client import MQTTv311

from os import path
import time
import traceback

from bits import Bits
from colours import *
from controller import Controller
from input_controller import InputController

class BLE2MQTT:
    def __init__(self, name):
        self.ble_name   = name
        self.topic_base = "-".join(self.ble_name.split(' '))

        self.mqtt = MQTT.Client(client_id=self.name(), clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")
        self.mqtt.will_set(self.topic("connected"), payload=b"false", qos=0, retain=True)

        self.ble_connected  = False
        self.mqtt_connected = False

        self.ble_ctrl = None

    def __del__(self):
        if self.ble_ctrl:
            del self.ble_ctrl
        if self.mqtt_connected:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

    def _log(self, msg):
        print("{0} {1}".format(self, msg))

    def _logble(self, msg):
        self._log("[{0}] {1}".format(style("BLE", Colours.FG.CYAN), msg))

    def _logmqtt(self, msg):
        self._log("[{0}] {1}".format(style("MQTT", Colours.FG.BLUE), msg))

    def _error(self, e=None, tb=True):
        if e:
            self._log(style(type(e).__name__, Colours.FG.RED) + ": {}".format(e))
            if tb: 
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

    ###########################################################################
    ## BLUETOOTH

    def ble_connect(self):
        try:
            self._logble("Attempting connect...")
            self.ble_ctrl = InputController(ctrl_name=self.ble_name)
        except Exception as e:
            self._error(e, tb=False)
            self.ble_connected = False
        else:
            self._logble(style("Connected", Colours.FG.GREEN))
            self.ble_connected = True  # OK

    def ble_get(self):
        """Returns topic, value pair"""
        return self.ble_ctrl.read_next()


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
                    + " with result code {}".format(rc))

    def _on_message(self, client, userdata, msg):
        self._logmqtt("Received on '{0}' ({1}): {2}".format(
                msg.topic, msg.qos,
                Bits.bytes_to_str(msg.payload)))

    def mqtt_connect(self, host, port=1883, lifetime=60):
        self.mqtt.on_connect    = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect
        self.mqtt.on_message    = self._on_message

        try:
            self._logmqtt("Trying to connect to {0}:{1}...".format(host, port))
            self.mqtt.connect(host, port, lifetime)
            # self.mqtt_connected = True
        except Exception as e:
            self._error(e, tb=False)
            self.mqtt_connected = False

    def mqtt_publish(self, topic, payload, qos=0, retain=False):
        topic = self.topic(topic)

        self._logmqtt("Publishing to '{0}': {1}".format(topic, Bits.bytes_to_str(payload)))
        self.mqtt.publish(topic, Bits.str_to_bytes(payload), qos, retain)


    ###########################################################################
    ## General

    def start(self):
        self.mqtt.loop_start()
        time.sleep(1)

        try:
            while self.ble_connected and self.mqtt_connected:
                topic, value = self.ble_get()
                if topic and value is not None:
                    self.mqtt_publish(topic, value)
        except KeyboardInterrupt:
            self.mqtt.disconnect()
            self.mqtt_connected = False

if __name__ == "__main__":
    client = BLE2MQTT("Xbox Wireless Controller")
    client.ble_connect()
    # client.mqtt_connect("127.0.0.1")
    # DONT USE PUBLIC IP, OTHERWISE TELENET WILL KICK ME FROM THE INTERNET 
    client.mqtt_connect(host="192.168.0.175", port=1883)
    client.start()
