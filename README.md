# cesu_8_modifier

Decodes CESU-8 (Compatibility Encoding Scheme for UTF-16) byte sequences into Python strings, combining surrogate pairs into single supplementary code points.

```python
from cesu_8_modifier import decode

# U+1F600 GRINNING FACE, encoded as a CESU-8 surrogate pair.
data = b"\xED\xA0\xBD\xED\xB8\x80"
assert decode(data) == "\U0001f600"
```

## Why this exists

CESU-8 is not UTF-8. It encodes each UTF-16 code unit separately, so characters outside the Basic Multilingual Plane become a pair of three-byte sequences that a standard UTF-8 decoder rejects. Python's built-in `bytes.decode` therefore cannot read CESU-8 produced by older Java serializers, MySQL `utf8` columns, or certain Oracle drivers. This module fills that gap with a strict decoder that accepts exactly the CESU-8 subset those systems emit: BMP code points and surrogate pairs, nothing else.

The deliberate trade-off is strictness. Malformed input — overlong encodings, lone surrogates, truncated sequences, four-byte UTF-8 — raises `CESU8DecodeError` rather than being silently replaced. If you need lenient behaviour, catch the exception and substitute U+FFFD yourself; the decoder will not guess.

## API

- `decode(data: bytes) -> str` — decode CESU-8 bytes. Accepts `bytes`, `bytearray`, or `memoryview`; raises `TypeError` for anything else. Raises `CESU8DecodeError` (a subclass of `ValueError`) for malformed input.
- `CESU8DecodeError` — the exception type raised for invalid CESU-8.

## The awkward edge

A high surrogate that is not followed by a low surrogate is an error, not a replacement character. That means `decode(b"\xED\xA0\xBD")` raises. This is intentional: in CESU-8, a lone surrogate is never a valid encoding of anything, and treating it as U+FFFD would hide data corruption. If you are decoding a stream that may legitimately contain lone surrogates (some Java `String` instances do), you must handle them before calling this decoder.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

