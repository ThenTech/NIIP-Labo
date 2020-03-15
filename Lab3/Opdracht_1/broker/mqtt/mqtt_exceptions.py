from mqtt.mqtt_packet_types import ReturnCode

class MQTTPacketException(Exception):
    """General exception."""
    pass

class MQTTTopicException(Exception):
    pass

class MQTTDisconnectError(Exception):
    """Exception that should always result in disconnect."""
    def __init__(self, *args, **kwargs):
        self.return_code = kwargs.pop("code", ReturnCode.NO_CODE)
        super().__init__(*args, **kwargs)
