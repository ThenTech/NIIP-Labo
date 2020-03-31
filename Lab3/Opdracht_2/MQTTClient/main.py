# https://github.com/eclipse/paho.mqtt.python
import paho.mqtt.client as MQTT
from paho.mqtt.client import MQTTv311

import time
import traceback

from bits import Bits
from colours import *
from controller import Controller, VirtualController


class MQTT2INPUT:
    def __init__(self, controller_name):
        self.topic_base = "-".join(controller_name.split(' '))

        self.mqtt = MQTT.Client(client_id=self.name(), clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")
        self.mqtt.will_set(self.topic("connected"), payload=b"false", qos=0, retain=True)

        self.mqtt_connected = False

        self._loginput("Creating virtual controller...")
        self.ctrl = VirtualController()
        self.ctrl.reset()

    def __del__(self):
        del self.ctrl

        if self.mqtt_connected:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

    def _log(self, msg):
        print("{0} {1}".format(self, msg))

    def _loginput(self, msg):
        self._log("[{0}] {1}".format(style("INPUT", Colours.FG.CYAN), msg))

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
        return style("<{0}, mqtt={2}>".format(self.name(), self.mqtt_connected), Colours.FG.YELLOW)

    def topic(self, name):
        sep = "/"
        if self.topic_base.endswith(sep):
            return self.topic_base + name
        else:
            return self.topic_base + sep + name

    def name(self):
        return "MQTT2INPUT"


    ###########################################################################
    ## MQTT

    def _on_connect(self, client, userdata, flags, rc):
        self._logmqtt(style("Connected", Colours.FG.GREEN) \
                    + " with result code {}".format(rc))

        # client.subscribe("$SYS/#")

        ## Subscribe to everything separately:
        # tops = Controller.values()
        # for t in tops:
        #     self._logmqtt("Subscribing to: '{0}'".format(t))
        # client.subscribe(list(map(lambda t: (t, 1), tops)))

        ## Or Subscribe to wildcards
        tops = (Controller.All.BUTTONS, Controller.All.STICKS , Controller.All.DPAD)
        tops = list(map(self.topic, tops))

        for t in tops:
            self._logmqtt("Subscribing to: '{0}'".format(t))
        client.subscribe(list(map(lambda t: (t, 1), tops)))

        # client.message_callback_add(sub, callback)

        self.mqtt_connected = True

    def _on_disconnect(self, client, userdata, rc):
        self._logmqtt(style("Disconnected", Colours.FG.RED) \
                    + " with result code {}".format(rc))

    def _on_message(self, client, userdata, msg):
        self._logmqtt("Received on '{0}' ({1}): {2}".format(
                msg.topic, msg.qos,
                Bits.bytes_to_str(msg.payload)))

        if not msg.topic.startswith(self.topic_base) or "/" not in msg.topic:
            return

        topic = msg.topic.split('/', 1)[1]

        # Do something for each button/stick
        # First parse msg.payload, then update input state
        payload_str = Bits.bytes_to_str(msg.payload)

        if (topic.startswith("button") or topic.startswith("dpad")) and not "trigger" in topic:
            btn_state = False

            if payload_str == Controller.State.ON:
                btn_state = True
            elif payload_str == Controller.State.OFF:
                btn_state = False
            else:
                return

            self.ctrl.set_value(topic, btn_state)
        elif topic.startswith("stick") or "trigger" in topic:
            # Extract value
            linear_value = Bits.unpack(msg.payload)
            self.ctrl.set_value(topic, linear_value)

    def mqtt_connect(self, host, port=1883, lifetime=60):
        self.mqtt.on_connect    = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect
        self.mqtt.on_message    = self._on_message

        try:
            self._logmqtt("Trying to connect to {0}:{1}...".format(host, port))
            self.mqtt.connect(host, port, lifetime)
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
        # Loop a couple of times to ensure connection
        while not self.mqtt_connected:
            self.mqtt.loop()
            time.sleep(1)

        if not self.mqtt_connected:
            self._logmqtt(style("Warning: Not connected?", Colours.FG.BRIGHT_RED))
            return

        self._log("Listening for MQTT packets to control the VirtualController...")

        try:
            self.mqtt.loop_forever()
        except KeyboardInterrupt:
            self.mqtt.disconnect()
            self.mqtt_connected = False


if __name__ == "__main__":
    client = MQTT2INPUT("Xbox Wireless Controller")
    # client.mqtt_connect("127.0.0.1")
    client.mqtt_connect(host="apps.bramkelchtermans.be", port=1883)
    client.start()
