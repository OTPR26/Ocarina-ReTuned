#!/usr/bin/env python3
"""Validate the GNU unwind-index encoding consumed by the static Switch host."""
import argparse
from pathlib import Path
import struct


def check(path):
    data = Path(path).read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected little-endian ELF64')
    section_offset = struct.unpack_from('<Q', data, 40)[0]
    entry_size, count, names_index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, section_offset+i*entry_size) for i in range(count)]
    names = sections[names_index]
    names_data = data[names[4]:names[4]+names[5]]
    by_name = {names_data[s[0]:].split(b'\0',1)[0].decode():s for s in sections}
    h = by_name['.eh_frame_hdr']
    frames = by_name['.eh_frame']
    header = data[h[4]:h[4]+h[5]]
    if header[:4] != b'\x01\x1b\x03\x3b':
        raise ValueError('unwind index encoding does not match Switch lookup')
    entries = struct.unpack_from('<I',header,8)[0]
    assert 12+entries*8 <= len(header)
    previous = -1
    for i in range(entries):
        pc_delta, fde_delta = struct.unpack_from('<ii',header,12+i*8)
        pc, address = h[3]+pc_delta, h[3]+fde_delta
        assert pc >= previous, 'unsorted unwind index'
        assert frames[3] <= address and address+16 <= frames[3]+frames[5]
        offset = frames[4]+address-frames[3]
        length, cie_delta, initial_delta, extent = struct.unpack_from('<IIiI',data,offset)
        assert length >= 12 and address+length+4 <= frames[3]+frames[5]
        assert address+8+initial_delta == pc, 'FDE PC encoding mismatch'
        assert extent > 0, 'empty indexed unwind extent'
        previous = pc
    print(f'PASS: {entries} sorted FDE entries match the Switch lookup encoding')
    return entries


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf',type=Path)
    check(parser.parse_args().elf)
