#############
# Bit helpers
class Bits:
    @staticmethod
    def bit(idx, val, size = 1):
        val = val & ((1 << size) - 1)
        return (val << idx)

    @staticmethod
    def get(val, idx, size = 1):
        return ((val >> idx) & ((1 << size) - 1))

    @staticmethod
    def to_single_byte(raw):
        if isinstance(raw, bytes):
            return int(raw[0])
        return raw
