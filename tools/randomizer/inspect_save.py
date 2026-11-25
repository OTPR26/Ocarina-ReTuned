#!/usr/bin/env python3
"""Read and validate an isolated proof save without changing it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(profile, slot):
    if slot not in range(3):
        raise ValueError('Slot must be 0, 1, or 2')
    identity = (profile / 'identity').read_bytes()
    fields = identity.decode('ascii').splitlines()
    if (len(fields) != 4 or fields[0] != 'retuned-randomizer-save-v1'
            or any(not re.fullmatch('[0-9a-f]{64}', x) for x in fields[1:3])):
        raise ValueError('Invalid profile identity')
    size = int(fields[3])
    if not 4 <= size <= 1024 * 1024:
        raise ValueError('Invalid extended-state size')
    native = (profile / 'native' / f'save0{slot}.bin').read_bytes()
    if len(native) != 0x14dc or native[0x30:0x36] != b'ZELDAZ':
        raise ValueError('Not a populated canonical proof save')
    record = (profile / f'slot{slot}-{digest(native)}.state').read_bytes()
    if (len(record) != len(identity) + len(native) + size + 64
            or record[:len(identity)] != identity
            or record[len(identity):len(identity)+len(native)] != native
            or record[-64:] != digest(record[:-64]).encode('ascii')):
        raise ValueError('Paired save is corrupt or does not match')
    extended = record[len(identity)+len(native):-64]
    u16 = lambda at: struct.unpack_from('<H', native, at)[0]
    u32 = lambda at: struct.unpack_from('<I', native, at)[0]
    # Canonical guest SaveContext fields from the pinned z3D.h ABI.
    return {
        'slot': slot, 'seed_sha256': fields[1], 'runtime_sha256': fields[2],
        'native_sha256': digest(native), 'extended_sha256': digest(extended),
        'extended_version': struct.unpack_from('<I', extended)[0],
        'save_count': u16(0x36), 'health_capacity': u16(0x42),
        'magic_acquired': native[0x4e], 'equipment': u16(0xb6),
        'quest_items': u32(0xbc), 'inventory': list(native[0x8c:0xa6]),
        'opened_chests': {str(scene): u32(0xec + scene * 0x1c)
                          for scene in range(124) if u32(0xec + scene * 0x1c)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('--slot', type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(inspect(args.profile, args.slot), indent=2))
