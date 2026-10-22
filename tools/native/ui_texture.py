"""Bounded single-texture RGBA4 CTXB conversion for local ROM preparation.

Only container/texture layout is described here. No game pixels are included.
Channel order matches the native PICA RGBA4444 decoder (R in bits 12..15).
"""
import struct


def _morton(x, y):
    return ((x & 1) | ((y & 1) << 1) | ((x & 2) << 1) |
            ((y & 2) << 2) | ((x & 4) << 2) | ((y & 4) << 3))


def _dimensions(width, height):
    if (not 8 <= width <= 2048 or not 8 <= height <= 2048 or
            width % 8 or height % 8):
        raise ValueError('Unsupported local UI texture dimensions')


def decode(data):
    """Return width, height and linear RGBA8 bytes; reject ambiguous layouts."""
    if len(data) < 72 or len(data) > 9 * 1024**2 or data[:4] != b'ctxb':
        raise ValueError('Invalid UI CTXB header')
    size, count = struct.unpack_from('<II', data, 4)
    chunk, payload = struct.unpack_from('<II', data, 16)
    if (size != len(data) or count != 1 or chunk < 24 or
            chunk + 48 != payload or data[chunk:chunk + 4] != b'tex ' or
            struct.unpack_from('<II', data, chunk + 4) != (48, 1)):
        raise ValueError('Unsupported UI CTXB container')
    length, mips, flags, width, height, fmt, dtype, relative = struct.unpack_from(
        '<IHHHHHHI', data, chunk + 12)
    _dimensions(width, height)
    if (mips != 1 or flags != 0 or fmt != 0x6752 or dtype != 0x8033 or
            relative != 0 or length != width * height * 2 or payload + length != len(data)):
        raise ValueError('Expected one complete RGBA4 UI texture')
    rgba = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            tiled = ((y // 8) * (width // 8) + x // 8) * 64 + _morton(x, y)
            value = struct.unpack_from('<H', data, payload + tiled * 2)[0]
            at = (y * width + x) * 4
            rgba[at:at + 4] = bytes(((value >> shift) & 15) * 17 for shift in (12, 8, 4, 0))
    return width, height, bytes(rgba)


def encode(template, width, height, rgba):
    """Keep validated local texture metadata, replacing dimensions and pixels."""
    decode(template)
    _dimensions(width, height)
    if len(rgba) != width * height * 4:
        raise ValueError('RGBA buffer does not match texture dimensions')
    chunk, payload = struct.unpack_from('<II', template, 16)
    output = bytearray(template[:payload]) + bytearray(width * height * 2)
    struct.pack_into('<I', output, 4, len(output))
    struct.pack_into('<I', output, chunk + 12, width * height * 2)
    struct.pack_into('<HH', output, chunk + 20, width, height)
    for y in range(height):
        for x in range(width):
            at = (y * width + x) * 4
            value = 0
            for channel in rgba[at:at + 4]:
                value = (value << 4) | ((channel * 15 + 127) // 255)
            tiled = ((y // 8) * (width // 8) + x // 8) * 64 + _morton(x, y)
            struct.pack_into('<H', output, payload + tiled * 2, value)
    return bytes(output)


# ETC1 block decoding adapted from Scarlet (MIT).
# Copyright (c) 2016 xdaniel (Daniel R.) / DigitalZero Domain.
# Full notice: resources/licenses/scarlet-MIT.txt
MODIFIERS = (
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183),
)


def clamp(value: int) -> int:
    return max(0, min(255, value))


def _decode_etc1_block(block: int) -> list[tuple[int, int, int]]:
    table1 = (block >> 37) & 7
    table2 = (block >> 34) & 7
    differential = (block >> 33) & 1
    flip = (block >> 32) & 1

    if not differential:
        r1n, r2n = (block >> 60) & 15, (block >> 56) & 15
        g1n, g2n = (block >> 52) & 15, (block >> 48) & 15
        b1n, b2n = (block >> 44) & 15, (block >> 40) & 15
        r1, r2 = r1n * 17, r2n * 17
        g1, g2 = g1n * 17, g2n * 17
        b1, b2 = b1n * 17, b2n * 17
    else:
        def signed3(value: int) -> int:
            return value - 8 if value >= 4 else value

        r1n, g1n, b1n = (block >> 59) & 31, (block >> 51) & 31, (block >> 43) & 31
        r2n = r1n + signed3((block >> 56) & 7)
        g2n = g1n + signed3((block >> 48) & 7)
        b2n = b1n + signed3((block >> 40) & 7)
        r1, r2 = (r1n << 3) | (r1n >> 2), (r2n << 3) | (r2n >> 2)
        g1, g2 = (g1n << 3) | (g1n >> 2), (g2n << 3) | (g2n >> 2)
        b1, b2 = (b1n << 3) | (b1n >> 2), (b2n << 3) | (b2n >> 2)

    pixels: list[tuple[int, int, int]] = []
    for py in range(4):
        for px in range(4):
            bit = px * 4 + py
            index = ((block >> bit) & 1) | (((block >> (bit + 16)) & 1) << 1)
            first = (flip and py < 2) or (not flip and px < 2)
            base = (r1, g1, b1) if first else (r2, g2, b2)
            modifier = MODIFIERS[table1 if first else table2][index]
            pixels.append(tuple(clamp(channel + modifier) for channel in base))
    return pixels



def decode_compressed(data):
    """Decode one original ETC1/ETC1A4 CTXB from the user's local ROM."""
    if len(data) < 72 or len(data) > 9 * 1024**2 or data[:4] != b'ctxb':
        raise ValueError('Invalid compressed UI CTXB')
    size, count = struct.unpack_from('<II', data, 4)
    chunk, payload = struct.unpack_from('<II', data, 16)
    if (size != len(data) or count != 1 or chunk < 24 or chunk + 48 != payload or
            data[chunk:chunk + 4] != b'tex ' or
            struct.unpack_from('<II', data, chunk + 4) != (48, 1)):
        raise ValueError('Unsupported compressed UI container')
    length, mips, flags, width, height, fmt, dtype, relative = struct.unpack_from(
        '<IHHHHHHI', data, chunk + 12)
    _dimensions(width, height)
    alpha4 = fmt == 0x675b
    if (fmt not in (0x675a, 0x675b) or mips != 1 or flags not in (0, 1) or
            dtype != 0 or relative or length != width * height // (1 if alpha4 else 2) or
            payload + length != len(data)):
        raise ValueError('Expected complete ETC1 UI texture')
    rgba = bytearray(width * height * 4)
    cursor = payload
    for ty in range(0, height, 8):
        for tx in range(0, width, 8):
            for by in range(0, 8, 4):
                for bx in range(0, 8, 4):
                    alpha = struct.unpack_from('<Q', data, cursor)[0] if alpha4 else 2**64 - 1
                    cursor += 8 if alpha4 else 0
                    colors = _decode_etc1_block(struct.unpack_from('<Q', data, cursor)[0])
                    cursor += 8
                    for y in range(4):
                        for x in range(4):
                            at = ((ty + by + y) * width + tx + bx + x) * 4
                            a = ((alpha >> ((x * 4 + y) * 4)) & 15) * 17
                            rgba[at:at + 4] = bytes((*colors[y * 4 + x], a))
    return width, height, bytes(rgba)
