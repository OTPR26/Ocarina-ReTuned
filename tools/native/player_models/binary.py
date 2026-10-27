"""Bounded archive reads for native actor files supplied by the user."""
import struct
from .reader import require


def take(data, offset, size):
    require(offset >= 0 and size >= 0 and offset + size <= len(data), "Actor range is outside file")
    return bytes(data[offset:offset + size])


def u(data, offset):
    return struct.unpack('<I', take(data, offset, 4))[0]


def h(data, offset):
    return struct.unpack('<H', take(data, offset, 2))[0]


def entries(d):
    require(d[:4] in (b"GAR\2", b"ZAR\1") and u(d, 4) == len(d), "Invalid native actor archive")
    mm = d[:4] == b"GAR\2"
    meta = u(d, 16)
    offsets = u(d, 20)
    require(0 < h(d, 10) <= 4096, "Invalid actor archive count")
    result = []
    for i in range(h(d, 10)):
        at = meta + i * (12 if mm else 8)
        np = u(d, at + (8 if mm else 4))
        end = d.find(b"\0", np)
        require(0 <= np < end < len(d), "Invalid actor resource name")
        offset = u(d, offsets + i * 4)
        result.append(
            (take(d, np, end - np).decode(), offset, take(d, offset, u(d, at)))
        )
    return result

