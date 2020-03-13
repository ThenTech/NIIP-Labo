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

    @staticmethod
    def pad_bytes(val, size):
        assert(size >= 0)

        length = len(val)
        if length < size:
            val = bytes(size - length) + val

        return val

    @staticmethod
    def pack(val, size):
        bb = b""
        while val > 0:
            bb = bytes((val & 0xFF,)) + bb
            val >>= 8
        return Bits.pad_bytes(bb, size)
