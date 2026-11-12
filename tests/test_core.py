import unittest

from cesu_8_modifier import CESU8DecodeError, decode


class TestDecode(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(decode(b"hello"), "hello")

    def test_two_byte_bmp(self):
        # U+00E9 LATIN SMALL LETTER E WITH ACUTE
        self.assertEqual(decode(b"\xC3\xA9"), "\u00e9")

    def test_three_byte_bmp(self):
        # U+20AC EURO SIGN
        self.assertEqual(decode(b"\xE2\x82\xAC"), "\u20ac")

    def test_surrogate_pair(self):
        # U+1F600 GRINNING FACE encoded as CESU-8 surrogate pair.
        self.assertEqual(decode(b"\xED\xA0\xBD\xED\xB8\x80"), "\U0001f600")

    def test_mixed_content(self):
        data = b"a\xC3\xA9\xE2\x82\xAC\xED\xA0\xBD\xED\xB8\x80z"
        self.assertEqual(decode(data), "a\u00e9\u20ac\U0001f600z")

    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_bytearray_accepted(self):
        self.assertEqual(decode(bytearray(b"\xC3\xA9")), "\u00e9")

    def test_memoryview_accepted(self):
        self.assertEqual(decode(memoryview(b"\xC3\xA9")), "\u00e9")

    def test_rejects_str(self):
        with self.assertRaises(TypeError):
            decode("\u00e9")

    def test_rejects_int(self):
        with self.assertRaises(TypeError):
            decode(42)

    def test_rejects_truncated_two_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xC3")

    def test_rejects_truncated_three_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xE2\x82")

    def test_rejects_overlong_two_byte(self):
        # 0xC0 0x80 would decode to U+0000 but is overlong.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xC0\x80")

    def test_rejects_overlong_three_byte(self):
        # 0xE0 0x80 0x80 would decode to U+0000 but is overlong.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xE0\x80\x80")

    def test_rejects_four_byte_sequence(self):
        # Standard UTF-8 for U+1F600; CESU-8 must not accept it.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xF0\x9F\x98\x80")

    def test_rejects_lone_high_surrogate(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\xBD")

    def test_rejects_lone_low_surrogate(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xB8\x80")

    def test_rejects_high_surrogate_followed_by_bmp(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\xBD\x41")

    def test_rejects_high_surrogate_followed_by_high_surrogate(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\xBD\xED\xA0\xBD")

    def test_rejects_bare_surrogate_encoding(self):
        # 0xED 0xA0 0x80 is the UTF-8 form of U+D800; CESU-8 does not allow
        # encoding a surrogate as a standalone code point.
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\x80")

    def test_rejects_invalid_continuation(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xC3\x28")

    def test_rejects_invalid_lead_byte(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\x80")

    def test_rejects_0xfe(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xFE")

    def test_rejects_0xff(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xFF")

    def test_high_surrogate_at_end(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\xBD")

    def test_high_surrogate_followed_by_truncated_low(self):
        with self.assertRaises(CESU8DecodeError):
            decode(b"\xED\xA0\xBD\xED\xB8")

    def test_round_trip_supplementary(self):
        # Encode a supplementary character as CESU-8 and decode it back.
        s = "\U0001f600"
        high = 0xD800 + ((ord(s) - 0x10000) >> 10)
        low = 0xDC00 + ((ord(s) - 0x10000) & 0x3FF)
        def enc(cp):
            return bytes([
                0xE0 | (cp >> 12),
                0x80 | ((cp >> 6) & 0x3F),
                0x80 | (cp & 0x3F),
            ])
        self.assertEqual(decode(enc(high) + enc(low)), s)


if __name__ == "__main__":
    unittest.main()
