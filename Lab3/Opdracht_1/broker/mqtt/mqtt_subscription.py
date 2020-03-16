from mqtt.bits import Bits
from mqtt.mqtt_packet_types import WillQoS
from mqtt.topic_matcher import TopicMatcher

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
        topic = Bits.bytes_to_str(topic)
        # print("Subscribed topic: " + self.topic)
        # print("Check topic     : " + topic)
        return TopicMatcher(self.topic).matches(topic)

    def update_qos(self, qos):
        self.qos = qos if qos in WillQoS.CHECK_VALID else 0

    @staticmethod
    def filter_wildcards(sub_topic, pub_topic=b""):
        tm = TopicMatcher(sub_topic)
        if pub_topic:
            tm.matches(Bits.bytes_to_str(pub_topic))
        return tm.filtered()
