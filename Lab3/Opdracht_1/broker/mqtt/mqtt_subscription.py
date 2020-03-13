from mqtt.mqtt_packet_types import WillQoS

class TopicSubscription:
    def __init__(self, order, topic, qos=0):
        super().__init__()
        self.order = order
        self.topic = topic
        self.qos   = qos

    def __str__(self):
        return "'{0}' ({1})".format(self.topic, self.qos)

    __repr__ = __str__

    def __lt__(self, other):
        return self.order < other.order

    def __le__(self, other):
        return self.order <= other.order

    def __eq__(self, other):
        return self.order == other.order

    def __gt__(self, other):
        return self.order > other.order

    def __ge__(self, other):
        return self.order >= other.order

    def matches(self, topic):
        # TODO match topic with self.topic, including wildcards
        return True

    def update_qos(self, qos):
        self.qos = qos if qos in WillQoS.CHECK_VALID else 0

    @staticmethod
    def filter_wildcards(topic_name):
        # TODO
        return topic_name
