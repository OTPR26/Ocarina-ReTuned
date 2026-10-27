"""
N64 (Fast3D) texture decoding to RGBA8, and format constants.

Used both for the software preview renderer and for re-emitting textures as
SoH Texture resources. Formats follow the F3DEX2 G_IM_FMT / G_IM_SIZ enums.
"""
from __future__ import annotations
import numpy as np

# G_IM_FMT
G_IM_FMT_RGBA = 0
G_IM_FMT_YUV = 1
G_IM_FMT_CI = 2
G_IM_FMT_IA = 3
G_IM_FMT_I = 4

# G_IM_SIZ
G_IM_SIZ_4b = 0
G_IM_SIZ_8b = 1
G_IM_SIZ_16b = 2
G_IM_SIZ_32b = 3

SIZ_BITS = {0: 4, 1: 8, 2: 16, 3: 32}

# SoH/libultraship TextureType enum (matches ZAPD TextureType ordering)
# used when emitting Texture resources
SOH_TEX_TYPE = {
    (G_IM_FMT_RGBA, G_IM_SIZ_16b): 1,   # RGBA16
    (G_IM_FMT_RGBA, G_IM_SIZ_32b): 2,   # RGBA32
    (G_IM_FMT_CI, G_IM_SIZ_4b): 3,      # Palette4bpp (CI4)
    (G_IM_FMT_CI, G_IM_SIZ_8b): 4,      # Palette8bpp (CI8)
    (G_IM_FMT_IA, G_IM_SIZ_4b): 5,      # Grayscale+Alpha 4bpp
    (G_IM_FMT_IA, G_IM_SIZ_8b): 6,      # GrayscaleAlpha8bpp (IA8)
    (G_IM_FMT_IA, G_IM_SIZ_16b): 7,     # GrayscaleAlpha16bpp (IA16)
    (G_IM_FMT_I, G_IM_SIZ_4b): 8,       # Grayscale4bpp (I4)
    (G_IM_FMT_I, G_IM_SIZ_8b): 9,       # Grayscale8bpp (I8)
}


def _rgba5551_to_rgba8(px: np.ndarray) -> np.ndarray:
    """px: uint16 array -> (...,4) uint8"""
    r = ((px >> 11) & 0x1F).astype(np.uint16)
    g = ((px >> 6) & 0x1F).astype(np.uint16)
    b = ((px >> 1) & 0x1F).astype(np.uint16)
    a = (px & 1).astype(np.uint16)
    out = np.empty(px.shape + (4,), np.uint8)
    out[..., 0] = (r * 255 // 31)
    out[..., 1] = (g * 255 // 31)
    out[..., 2] = (b * 255 // 31)
    out[..., 3] = np.where(a == 1, 255, 0)
    return out


def decode(data: bytes, fmt: int, siz: int, width: int, height: int,
           tlut: bytes = b"") -> np.ndarray:
    """Decode raw N64 texel data -> H*W*4 uint8 RGBA array (row-major, top-left)."""
    n = width * height
    out = np.zeros((height, width, 4), np.uint8)

    if fmt == G_IM_FMT_RGBA and siz == G_IM_SIZ_16b:
        px = np.frombuffer(data[:n * 2], dtype=">u2").astype(np.uint16)
        out = _rgba5551_to_rgba8(px).reshape(height, width, 4)

    elif fmt == G_IM_FMT_RGBA and siz == G_IM_SIZ_32b:
        arr = np.frombuffer(data[:n * 4], dtype=np.uint8).reshape(height, width, 4)
        out = arr.copy()

    elif fmt == G_IM_FMT_IA and siz == G_IM_SIZ_16b:
        arr = np.frombuffer(data[:n * 2], dtype=np.uint8).reshape(height, width, 2)
        i = arr[..., 0]; a = arr[..., 1]
        out[..., 0] = i; out[..., 1] = i; out[..., 2] = i; out[..., 3] = a

    elif fmt == G_IM_FMT_IA and siz == G_IM_SIZ_8b:
        b = np.frombuffer(data[:n], dtype=np.uint8).reshape(height, width)
        i = ((b >> 4) & 0xF) * 17
        a = (b & 0xF) * 17
        out[..., 0] = i; out[..., 1] = i; out[..., 2] = i; out[..., 3] = a

    elif fmt == G_IM_FMT_IA and siz == G_IM_SIZ_4b:
        raw = np.frombuffer(data[:(n + 1) // 2], dtype=np.uint8)
        nib = _unpack_nibbles(raw, n).reshape(height, width)
        i = ((nib >> 1) & 0x7) * 36
        a = np.where((nib & 1) == 1, 255, 0)
        out[..., 0] = i; out[..., 1] = i; out[..., 2] = i; out[..., 3] = a

    elif fmt == G_IM_FMT_I and siz == G_IM_SIZ_8b:
        b = np.frombuffer(data[:n], dtype=np.uint8).reshape(height, width)
        out[..., 0] = b; out[..., 1] = b; out[..., 2] = b; out[..., 3] = b

    elif fmt == G_IM_FMT_I and siz == G_IM_SIZ_4b:
        raw = np.frombuffer(data[:(n + 1) // 2], dtype=np.uint8)
        nib = _unpack_nibbles(raw, n).reshape(height, width) * 17
        out[..., 0] = nib; out[..., 1] = nib; out[..., 2] = nib; out[..., 3] = nib

    elif fmt == G_IM_FMT_CI and siz == G_IM_SIZ_8b:
        idx = np.frombuffer(data[:n], dtype=np.uint8).reshape(height, width)
        pal = _decode_tlut(tlut, 256)
        out = pal[idx]

    elif fmt == G_IM_FMT_CI and siz == G_IM_SIZ_4b:
        raw = np.frombuffer(data[:(n + 1) // 2], dtype=np.uint8)
        idx = _unpack_nibbles(raw, n).reshape(height, width)
        pal = _decode_tlut(tlut, 16)
        out = pal[idx]

    else:
        # unsupported -> magenta placeholder so it is visually obvious
        out[..., 0] = 255; out[..., 2] = 255; out[..., 3] = 255

    return out


def _unpack_nibbles(raw: np.ndarray, count: int) -> np.ndarray:
    hi = (raw >> 4) & 0xF
    lo = raw & 0xF
    inter = np.empty(raw.size * 2, np.uint8)
    inter[0::2] = hi
    inter[1::2] = lo
    return inter[:count]


def _decode_tlut(tlut: bytes, entries: int) -> np.ndarray:
    """RGBA16 TLUT -> (entries,4) uint8 palette."""
    if not tlut:
        pal = np.zeros((entries, 4), np.uint8)
        pal[:, 3] = 255
        return pal
    px = np.frombuffer(tlut[:entries * 2], dtype=">u2").astype(np.uint16)
    pal = _rgba5551_to_rgba8(px)
    if pal.shape[0] < entries:
        pad = np.zeros((entries - pal.shape[0], 4), np.uint8)
        pal = np.vstack([pal, pad])
    return pal
