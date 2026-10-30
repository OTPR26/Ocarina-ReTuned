import struct


def elf(exports=(), imports=(), weak=()):
    names = bytearray(b'\0')
    symbols = bytearray(24)
    for values, binding, section in ((exports, 1, 1), (imports, 1, 0), (weak, 2, 0)):
        for name in values:
            symbols.extend(struct.pack('<IBBHQQ', len(names), binding << 4 | 2, 0, section, 0, 0))
            names.extend(name.encode() + b'\0')
    header = bytearray(64)
    header[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<Q', header, 40, 64)
    struct.pack_into('<HH', header, 58, 64, 3)
    sections = bytes(64)
    sections += struct.pack('<IIQQQQIIQQ', 0, 11, 0, 0, 256, len(symbols), 2, 0, 8, 24)
    sections += struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, 256 + len(symbols), len(names), 0, 0, 1, 0)
    return header + sections + symbols + names
