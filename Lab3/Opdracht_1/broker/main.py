from mqtt.mqtt_broker import MQTTBroker

if __name__ == "__main__":
    broker = MQTTBroker(host="", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host="10.42.0.1", port=MQTTBroker.PORT)
    # broker = MQTTBroker(host=MQTTBroker.HOST, port=MQTTBroker.PORT)
    broker.start()