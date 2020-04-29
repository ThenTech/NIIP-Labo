
class IPacket:
    def __init__(self, source_address, destination_address, source_ip=None, destination_ip=None, source_port=None, destination_port=None):
        super().__init__()


class Discover(IPacket):
    def __init__(self, source_address, destination_address):
        super().__init__(source_address, destination_address)

class Acknowledge(IPacket):
    ACK_DISCOVER = 1
    ACK_RECV     = 2

    TYPE = {
        ACK_DISCOVER: ACK_DISCOVER,
        ACK_RECV    : ACK_RECV    ,
    }

    def __init__(self, source_address, destination_address):
        super().__init__(source_address, destination_address)
