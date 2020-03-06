import pycom
import time
import machine
import ubinascii
import crypto
import os

import network
from machine import I2C, Pin
from uhashlib import sha256
import ujson

from mcp9808 import *
from requests import *

DEBUG = True
PAYLOAD_ENCRYPTED = False

def file_exists(name):
    try:
        os.stat(name)
    except:
        return False
    else:
        return True


class FireSensor:
    # LOCAL_SSID  = "EDM-Guest"
    # LOCAL_PASSW = "dulosi68"
    LOCAL_SSID  = "niip_bram"
    LOCAL_PASSW = "12345678"

    REMOTE_HOST = "10.42.0.1"
    REMOTE_PORT = 5000

    REMOTE_ROUTE_SIGNUP = "/sensors"    # Post {id, sig}
    REMOTE_ROUTE_CONFIG = "/config"     # Get  {id, sig} and recv {msg:{crit_temp, crit_msg}}
    REMOTE_ROUTE_NOTIFY = "/notify"     # Post {id, sig, msg}

    NOTIFY_MESSAGE = b"LP0 is on fire!"

    KEY_PRIVATE_DEVICE = "cert/private_key_1.pem"
    KEY_PUBLIC_SERVER  = "cert/public_key_2.pem"

    ALERT_PIN   = "P13"

    def __init__(self):
        super().__init__()

        self.settings = {
            "id"      : ubinascii.b2a_base64(ubinascii.hexlify(machine.unique_id())).strip(),
            "verified": 0,
            "t_thresh": 6000,
            "msg"     : self.NOTIFY_MESSAGE,
            "t_idle"  : 4550
        }

        self.wlan = None
        self.sock = None

        self.i2c       = None
        self.tsense    = None
        self.alert_pin = None

        with open(self.KEY_PRIVATE_DEVICE) as key:
            self.key_privdev = key.read()

        if file_exists(self.KEY_PUBLIC_SERVER):
            with open(self.KEY_PUBLIC_SERVER) as key:
                self.key_pubremote = key.read()
        else:
            self.key_pubremote = "" # Set after config

        self.check_nvram()

        self.signature_json = {
            "id"        : self.settings["id"],
            "signature" : ubinascii.b2a_base64(self.get_signature(self.settings["id"] + "_niip"))
        }

    def __del__(self):
        self.store_settings()

    @staticmethod
    def _get_from_ram(key):
        try:
            return pycom.nvs_get(key)
        except ValueError:
            return None

    def check_nvram(self):
        nvram_settings = { k: self._get_from_ram(k) for k in self.settings.keys() }

        if all(v is not None for v in nvram_settings.values()):
            # All were set, so use these values
            for k in self.settings.keys():
                self.settings[k] = nvram_settings[k]
        else:
            # Not all were set, so replace
            self.store_settings()

    def store_settings(self):
        for k in self.settings.keys():
            pycom.nvs_set(k, self.settings[k])

    def log(self, msg):
        if DEBUG:
            print(msg)

    def on_error(self, msg=""):
        pycom.rgbled(0xFF0000)
        print("Error: " + msg)
        time.sleep(5)
        machine.reset()

    def get_checksum(self, msg):
        return ubinascii.b2a_base64(ubinascii.hexlify(sha256(msg).digest()))

    def get_signature(self, msg):
        return crypto.generate_rsa_signature(msg, self.key_privdev)

    def rsa_encrypt(self, msg):
        if not self.key_pubremote: self.on_error("No public key!")
        return ubinascii.b2a_base64(crypto.rsa_encrypt(msg, self.key_pubremote))

    def rsa_decrypt(self, enc):
        return crypto.rsa_decrypt(ubinascii.a2b_base64(enc), self.key_privdev)

    def connect_wlan(self):
        self.log("Attempt to connect to WLAN...")

        if not self.wlan:
            self.wlan = network.WLAN(mode=network.WLAN.STA, power_save=True)
            self.wlan.connect(self.LOCAL_SSID, auth=(network.WLAN.WPA2, self.LOCAL_PASSW))

            if Retrier(self.wlan.isconnected, tries=10, delay_ms=500).attempt():
                # print(wlan.ifconfig())
                self.log("WLAN connected.")
                return True
            else:
                self.on_error("Timeout connecting to WiFi!")
                self.wlan = None
                return False
        else:
            self.log("WLAN already connected.")
            return True

    def connect_sensor(self):
        self.log("Attempt to connect sensor...")

        if not self.tsense:
            self.i2c = I2C(0, I2C.MASTER, baudrate=100000)

            try:
                self.tsense = MCP9808(self.i2c)
            except Exception as e:
                self.on_error("Could not connect to temperature sensor! " + str(e))
                self.tsense = None
                return False
            else:
                self.log("Sensor OK")
                # print("Temperature: {0:.2f}°C".format(self.tsense.get_temp()))

                # Set wakeup pin to temp sense interrupt pin
                self.alert_pin = Pin(self.ALERT_PIN, mode=Pin.IN, pull=Pin.PULL_UP)
                machine.pin_sleep_wakeup((self.ALERT_PIN,), machine.WAKEUP_ALL_LOW, enable_pull=True)
                return True
        else:
            self.log("Sensor already OK")
            return True

    def setup_from_remote(self):
        self.log("Attempt to setup from remote...")

        if not bool(self.settings["verified"]):
            if self.reconnect_to_remote():
                data = b""
                signature_json = ujson.dumps(self.signature_json)

                # Exchange id and request settings
                request = PostRequest(self.REMOTE_ROUTE_SIGNUP)
                request.add_header(Request.CONTENT_TYPE, Request.CONTENT_JSON)
                request.add_data(signature_json)

                self.log("Attempt to send SIGN-UP...")
                if Retrier(lambda: self.sock.send(request.get_payload()), tries=2, delay_ms=350).attempt():
                    # Successfully sent my id and signature, now request settings
                    self.log("Got SIGN-UP.")
                    time.sleep_ms(1000)

                    try:
                        response = self.sock.recv()
                        if response:
                            response = HttpResponse(response)
                            server_pubkey_json = response.getBody()
                            server_pubkey_json = ujson.loads(server_pubkey_json)
                            if "public_key" in server_pubkey_json:
                                self.key_pubremote = server_pubkey_json["public_key"]
                                self.key_pubremote = ubinascii.a2b_base64(self.key_pubremote)
                            else:
                                self.on_error("Did not receive public key after signing on?")
                                return False
                        else:
                            self.on_error("Did not receive response after signing on?")
                            return False
                    except Exception as e:
                        self.on_error("Signature response: " + str(e))
                        return False

                    if not self.key_pubremote:
                        self.on_error("No pub key?")
                        return False
                    else:
                        # Save key locally
                        with open(self.KEY_PUBLIC_SERVER, "w") as key:
                            key.write(self.key_pubremote)

                    if not self.reconnect_to_remote():
                        self.on_error("Could not reconnect!")

                    request = GetRequest(self.REMOTE_ROUTE_CONFIG)
                    request.add_header(Request.CONTENT_TYPE, Request.CONTENT_JSON)
                    request.add_data(signature_json)

                    self.log("Attempt to request CONFIG...")
                    if Retrier(lambda: self.sock.send(request.get_payload()), tries=2, delay_ms=350).attempt():
                        # Sent request, now recv settings
                        time.sleep_ms(500)
                        data = self.sock.recv()
                        self.log("Got CONFIG.")
                    else:
                        self.on_error("Could not sent config request!")
                        return False
                else:
                    self.on_error("Could not sent sign-on request!")
                    return False


                if data:
                    try:
                        response = HttpResponse(data)
                        data = response.getBody()
                        data = ujson.loads(data)
                    except Exception as e:
                        self.on_error("Could not parse config response! " + str(e))
                        return False

                    if "msg" in data:
                        if PAYLOAD_ENCRYPTED:
                            data = self.rsa_decrypt(data["msg"])
                            data = ujson.loads(data)
                        else:
                            data = data["msg"]

                        self.log("Got from remote: " + str(data))

                        if "crit_temp" in data:
                            self.settings["t_thresh"] = int(data["crit_temp"] * 100.0)
                            self.log("Set t_thresh={0}".format(self.settings["t_thresh"]))
                        else:
                            self.settings["t_thresh"] = 6000   # 60.00
                            self.log("No t_thresh, using default of {0}".format(self.settings["t_thresh"]))
                        if "crit_msg" in data:
                            self.settings["msg"] = data["crit_msg"]
                            self.log("Set msg='{0}'".format(self.settings["msg"]))

                        if self.connect_sensor():
                            self.tsense.set_alert_mode(enable_alert=True,
                                                       output_mode=ALERT_OUTPUT_INTERRUPT,
                                                       polarity=ALERT_POLARITY_ALOW,
                                                       selector=ALERT_SELECT_CRIT)
                            self.tsense.set_alert_boundary_temp(REG_TEMP_BOUNDARY_CRITICAL,
                                                                self.settings["t_thresh"] / 100.0)

                            self.log("Sensor configured for critical alert.")
                            self.settings["t_idle"]   = self.get_self_temperature() + 200
                            self.settings["verified"] = 1
                            return True
            else:
                return False
        else:
            self.log("Already verified")
            return True

    def connect_to_remote(self):
        self.log("Attempt to create and connect socket...")

        if not self.sock and self.connect_wlan():
            try:
                self.sock = FireSocket()
                self.sock.connect(self.REMOTE_HOST, self.REMOTE_PORT)
            except Exception as e:
                self.on_error("Could not create socket to remote! " + str(e))
                return False
            else:
                self.log("Socket OK")
                return True
        else:
            self.log("Socket already OK")
            return True

    def reconnect_to_remote(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        return self.connect_to_remote()

    def get_self_temperature(self):
        return int((machine.temperature() - 32) * 100 / 1.8)

    def check_sensor(self):
        self.log("Checking sensor value...")
        notify_server = False

        if self.connect_sensor():
            self.tsense.acknowledge_alert_irq()  # Is this needed in this case?

        measurement = self.get_self_temperature()

        if measurement >= self.settings["t_idle"] and measurement >= self.settings["t_thresh"] \
            and not (self.settings["t_idle"] > self.settings["t_thresh"]):
            # If self temperature is bigger than idle and threshold,
            # Continue to warn without checking sensor
            self.log("Warning: machine temperature already exceeds critical value!")
            notify_server = True
        else:
            measurement   = int(self.tsense.get_temp() * 100)
            notify_server = measurement >= self.settings["t_thresh"]

        if notify_server:
            # Threshold was hit, notify remote
            self.log("Notifying server...")
            if not self.connect_to_remote():
                self.on_error("Wanted to notify server, but could not be reached!")
                return

            message = {
                "temperature": float(measurement) / 100.0,
                "msg": self.settings["msg"]
            }
            message = ujson.dumps(message)

            signature_json = self.signature_json.copy()
            signature_json["msg"] = self.rsa_encrypt(message)

            payload_json = ujson.dumps(signature_json)

            request = PostRequest(self.REMOTE_ROUTE_NOTIFY)
            request.add_header(Request.CONTENT_TYPE, Request.CONTENT_JSON)
            request.add_data(payload_json)

            if Retrier(lambda: self.sock.send(request.get_payload()), tries=2, delay_ms=350).attempt():
                # Successfully sent notify
                self.log("Sent notify: " + message)
                self.go_to_sleep()
            else:
                self.on_error("Could not inform server of fire!!")
        else:
            self.log("Temperature below critical value.")
            self.go_to_sleep()

    def go_to_sleep(self):
        self.log("Going to sleep...")
        self.store_settings()
        # machine.deepsleep(5000)
        machine.deepsleep()

# Main
if __name__ == "__main__":
    print("Boot")

    rst = machine.reset_cause()

    if rst != machine.DEEPSLEEP_RESET:
        # Normal reset, not from being awoken
        print("Wake on RESET")

        # Configure as fire sensor
        pycom.heartbeat(False)
        pycom.wifi_on_boot(False)

        # If first boot, get settings from remote
        client = FireSensor()
        client.setup_from_remote()
        client.check_sensor()
    else:
        # Recover from deepsleep
        reason = machine.wake_reason()[0]

        if reason == machine.PIN_WAKE:
            print("Wake on PIN_INTERRUPT")

            client = FireSensor()

            # If not configured, get settings from remote
            client.setup_from_remote()

            # Take measurement, notify remote and go back to sleep
            client.check_sensor()
        else:
            print("Wake on ???")
