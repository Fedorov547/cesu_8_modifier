"""CESU-8 modifier decoder.

CESU-8 is a compatibility encoding used by some Java and database systems. It
encodes each UTF-16 code unit as its own UTF-8-like sequence, so a
supplementary character (U+10000 and above) becomes a pair of three-byte
sequences representing a high surrogate and a low surrogate. Standard UTF-8
decoders reject those surrogate sequences; this module combines them.

This implementation is deliberately strict: it accepts only well-formed CESU-8
for the BMP and for surrogate pairs, and rejects overlong encodings, lone
surrogates, truncated sequences, and code points above U+10FFFF. The trade-off
is that it will not silently repair malformed input, which is what you want
when the input is untrusted.
"""

from __future__ import annotations


class CESU8DecodeError(ValueError):
    """Raised when a byte sequence is not valid CESU-8."""


def _decode_one(data: bytes, pos: int) -> tuple[int, int]:
    """Decode one CESU-8 sequence starting at *pos*.

    Returns ``(code_unit, next_pos)`` where *code_unit* is a UTF-16 code unit
    (0..0xFFFF). Raises ``CESU8DecodeError`` on malformed input.
    """
    n = len(data)
    if pos >= n:
        raise CESU8DecodeError("unexpected end of input")
    b0 = data[pos]
    if b0 < 0x80:
        return b0, pos + 1
    if 0xC0 <= b0 < 0xE0:
        if pos + 1 >= n:
            raise CESU8DecodeError("truncated two-byte sequence")
        b1 = data[pos + 1]
        if b1 & 0xC0 != 0x80:
            raise CESU8DecodeError("invalid continuation byte")
        # Reject overlong encodings: C0 and C1 are never valid as lead bytes.
        if b0 < 0xC2:
            raise CESU8DecodeError("overlong two-byte sequence")
        return ((b0 & 0x1F) << 6) | (b1 & 0x3F), pos + 2
    if 0xE0 <= b0 < 0xF0:
        if pos + 2 >= n:
            raise CESU8DecodeError("truncated three-byte sequence")
        b1 = data[pos + 1]
        b2 = data[pos + 2]
        if b1 & 0xC0 != 0x80 or b2 & 0xC0 != 0x80:
            raise CESU8DecodeError("invalid continuation byte")
        # E0 A0..BF and ED 80..9F are the only legal ranges for the first
        # continuation byte; anything else is overlong.  ED A0..BF encodes a
        # surrogate code unit, which CESU-8 permits as half of a surrogate
        # pair; the pairing check happens in decode().
        if b0 == 0xE0 and b1 < 0xA0:
            raise CESU8DecodeError("overlong three-byte sequence")
        return ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F), pos + 3
    if 0xF0 <= b0 < 0xF8:
        # CESU-8 does not use four-byte sequences; supplementary characters
        # are always encoded as surrogate pairs.
        raise CESU8DecodeError("four-byte sequences are not valid CESU-8")
    raise CESU8DecodeError(f"invalid lead byte 0x{b0:02X}")


def decode(data: bytes) -> str:
    """Decode CESU-8 bytes into a Python ``str``.

    The input must be a ``bytes`` object. A ``bytearray`` or ``memoryview`` is
    accepted as well; anything else raises ``TypeError``. The result is a
    normal Python string, with surrogate pairs combined into a single code
    point.
    """
    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("decode() expects a bytes-like object")

    out: list[str] = []
    pos = 0
    n = len(data)
    while pos < n:
        unit, pos = _decode_one(data, pos)
        if 0xD800 <= unit <= 0xDBFF:
            # High surrogate: must be followed by a low surrogate.
            if pos >= n:
                raise CESU8DecodeError("lone high surrogate at end of input")
            low, pos = _decode_one(data, pos)
            if not (0xDC00 <= low <= 0xDFFF):
                raise CESU8DecodeError("high surrogate not followed by low surrogate")
            code_point = 0x10000 + ((unit - 0xD800) << 10) + (low - 0xDC00)
            out.append(chr(code_point))
        elif 0xDC00 <= unit <= 0xDFFF:
            raise CESU8DecodeError("lone low surrogate")
        else:
            out.append(chr(unit))
    return "".join(out)
