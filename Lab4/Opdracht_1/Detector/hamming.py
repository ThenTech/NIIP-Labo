"""
Adapted from: https://gist.github.com/joeladdison/5244877
"""
from bits import Bits
from bitarray import bitarray


class Hamming:
    # List of syndrome positions. SYNDROME_CHECK[pos] will give the
    # bit in the provided encoded byte that needs to be fixed
    # Note: bit order used is 7 6 5 4 3 2 1 0
    # SYNDROME_CHECK = [-1, 6, 5, 0, 4, 1, 2, 3]
    SYNDROME_CHECK = [-1, 6, 5, 4, 3, 2, 1, 0]

    @staticmethod
    def encode_nibble(data, with_parity=False):
        """
        Encode a nibble using Hamming encoding.
        Nibble is provided in form 0b0000DDDD == 0 0 0 0 D3 D2 D1 D0
        Encoded byte is in form (P) H2 H1 D3 H0 D2 D1 D0
        """
        # Get data bits
        d = [0, 0, 0, 0]
        d[0] = Bits.get(data, 3)
        d[1] = Bits.get(data, 2)
        d[2] = Bits.get(data, 1)
        d[3] = Bits.get(data, 0)

        # Calculate hamming bits
        h = [0, 0, 0]
        h[0] = (d[1] ^ d[2] ^ d[3])
        h[1] = (d[0] ^ d[2] ^ d[3])
        h[2] = (d[0] ^ d[1] ^ d[3])

        # Encode byte
        encoded = Bits.bit(6, h[2]) \
                | Bits.bit(5, h[1]) \
                | Bits.bit(4, d[0]) \
                | Bits.bit(3, h[0]) \
                | Bits.bit(2, d[1]) \
                | Bits.bit(1, d[2]) \
                | Bits.bit(0, d[3])

        if with_parity:
            # Calculate parity bit, using even parity
            p = 0 ^ d[0] ^ d[1] ^ d[2] ^ d[3] ^ h[0] ^ h[1] ^ h[2]
            encoded |= Bits.bit(7, p)

        return encoded

    @staticmethod
    def encode(raw_bytes, with_parity=False):
        """
        Encode bytes, per nibble, to bitarray.
        (result has multiple of 7 bits if with_parity=False else multiple of 8 bits.)
        """
        encoded = bitarray()
        pad = 8 if with_parity else 7

        for byte in raw_bytes:
            higher, lower = Bits.get(byte, 4, 4), Bits.get(byte, 0, 4)
            higher, lower = Hamming.encode_nibble(higher, with_parity), \
                            Hamming.encode_nibble(lower, with_parity)
            encoded += bitarray(Bits.bin(higher, pad) + Bits.bin(lower, pad))

        return encoded

    @staticmethod
    def decode_byte(byte, with_parity=False):
        """
        Decode a single hamming encoded byte, and return a decoded nibble.
        Input is in form (P) H2 H1 D3 H0 D2 D1 D0
        Decoded nibble is in form 0b0000DDDD == 0 0 0 0 D3 D2 D1 D0
        """
        error = 0
        corrected = 0

        # Calculate syndrome
        s = [0, 0, 0]

        d0, d1, d2, d3 = Bits.get(byte, 4), Bits.get(byte, 2), \
                         Bits.get(byte, 1), Bits.get(byte, 0)

        # D1 + D2 + D3 + H0
        s[0] = (d1 + d2 + d3 + Bits.get(byte, 3)) % 2

        # D0 + D2 + D3 + H1
        s[1] = (d0 + d2 + d3 + Bits.get(byte, 5)) % 2

        # D0 + D1 + D3 + H2
        s[2] = (d0 + d1 + d3 + Bits.get(byte, 6)) % 2

        syndrome = (s[0] << 2) | (s[1] << 1) | s[2]

        if syndrome:
            # Syndrome is not 0, so correct and log the error
            error += 1
            byte ^= (1 << Hamming.SYNDROME_CHECK[syndrome])
            corrected += 1

        # Check parity
        if with_parity:
            p = 0
            for i in range(0, 7):
                p ^= Bits.get(byte, i)

            if p != Bits.get(byte, 7):
                # Parity bit is wrong, so log error
                if syndrome:
                    # Parity is wrong and syndrome was also bad, so error is not corrected
                    corrected -= 1
                else:
                    # Parity is wrong and syndrome is fine, so corrected parity bit
                    error += 1
                    corrected += 1

        return (Bits.bit(3, Bits.get(byte, 4)) | Bits.get(byte, 0, 3), error, corrected)

    @staticmethod
    def decode(enc_bitarray, with_parity=False):
        """
        Decodes bitarray, per Hamming byte (7 bits if with_parity=False else 8 bits).
        """
        decoded = bitarray()
        pad     = 8 if with_parity else 7
        length  = enc_bitarray.length()
        index   = 0
        errors, corrections = 0, 0

        while index + pad <= length:
            ham_byte = enc_bitarray[index:index+pad]

            if not with_parity:
                # Insert 0 to make 8 bits long
                ham_byte.insert(0, 0)

            dec, err, cor = Hamming.decode_byte(Bits.unpack(ham_byte.tobytes()))

            errors      += err
            corrections += cor
            decoded     += bitarray(Bits.bin(dec, 4))
            index       += pad

        return (decoded, errors, corrections)


if __name__ == "__main__":
    def test(raw, errs=tuple(), with_parity=False):
        raw &= 0xf
        enc = Hamming.encode_nibble(raw, with_parity)

        for index in errs:
            if (with_parity and index < 8) or (not with_parity and index < 7):
                enc = Bits.set(enc, index, ~Bits.get(enc, index))

        dec, err, cor = Hamming.decode_byte(enc, with_parity)
        print(f"{Bits.bin(raw, 4)} => enc, dec = ({Bits.bin(enc, 7)}, {Bits.bin(dec, 4)}) == {raw == dec} ({err} errors, {cor} corrected)")

    test(0b0001)
    test(0b0101)
    test(0b0101, errs=(0,), with_parity=True)
    test(0b0101, errs=(0,6), with_parity=True)

    raw = b"\x15\x59"
    enc = Hamming.encode(raw)
    print(f"{Bits.bin(raw)} => {enc.to01()}")
    dec, err, cor = Hamming.decode(enc)
    print(f"{dec.to01()} ({err} errors, {cor} corrected) => {raw == dec.tobytes()}")
