
# https://github.com/eclipse/paho.mqtt.python
import paho.mqtt.client as MQTT
from paho.mqtt.client import MQTTv311

from os import path
import traceback

from bits import Bits
from colours import *
from controller import Controller


class MQTT2INPUT:
    def __init__(self, controller_name):
        self.topic_base = "-".join(controller_name.split(' '))

        self.mqtt = MQTT.Client(client_id=self.name(), clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")
        self.mqtt.will_set(self.topic("connected"), payload=b"false", qos=0, retain=True)

        self.mqtt_connected = False

    def __del__(self):
        if self.mqtt_connected:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

    def _log(self, msg):
        print("{0} {1}".format(self, msg))

    def _loginput(self, msg):
        self._log("[{0}] {1}".format(style("INPUT", Colours.FG.CYAN), msg))

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
        return style("<{0}, mqtt={2}>".format(self.name(), self.mqtt_connected), Colours.FG.YELLOW)

    def topic(self, name):
        return path.join(self.topic_base, name)

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
        tops = ("button/#", "trigger/#", "stick/#", "dpad/#")
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

        if topic.startswith("button") or topic.startswith("trigger") or topic.startswith("dpad"):
            btn_state = None

            if payload_str == Controller.State.ON:
                btn_state = True
            elif payload_str == Controller.State.OFF:
                btn_state = False
            else:
                return

            # TODO Send btn_state to button input defined by topic
            if topic == Controller.X:
                pass
            elif topic == Controller.Y:
                pass
            elif topic == Controller.A:
                pass
            elif topic == Controller.B:
                pass
            elif topic == Controller.LT:
                pass
            elif topic == Controller.RT:
                pass
            elif topic == Controller.START:
                pass
            elif topic == Controller.SELECT:
                pass
            elif topic == Controller.DPAD_UP:
                pass
            elif topic == Controller.DPAD_RIGHT:
                pass
            elif topic == Controller.DPAD_DOWN:
                pass
            elif topic == Controller.DPAD_LEFT:
                pass
        else:
            # Extract value
            linear_value = Bits.unpack(msg.payload)

            # TODO Send linear_value to stick input defined by topic
            if topic == Controller.LSTICK_UP:
                pass
            elif topic == Controller.LSTICK_RIGHT:
                pass
            elif topic == Controller.LSTICK_DOWN:
                pass
            elif topic == Controller.LSTICK_LEFT:
                pass
            elif topic == Controller.RSTICK_UP:
                pass
            elif topic == Controller.RSTICK_RIGHT:
                pass
            elif topic == Controller.RSTICK_DOWN:
                pass
            elif topic == Controller.RSTICK_LEFT:
                pass

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
        try:
            self.mqtt.loop_forever()
        except KeyboardInterrupt:
            self.mqtt.disconnect()
            self.mqtt_connected = False


if __name__ == "__main__":
    client = MQTT2INPUT("Xbox Wireless Controller")
    client.mqtt_connect("127.0.0.1")
    client.start()
