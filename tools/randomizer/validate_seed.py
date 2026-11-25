#!/usr/bin/env python3
"""Check development seed tables against the exact guest ABI; no activation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

REQUIRED = {'rItemOverrides', 'gSettingsContext', 'rDungeonRewardOverrides',
            'rShopsanityPrices', 'gSpoilerData', 'gSpoilerDataLocs', 'rDungeonImportance',
            'rEntranceOverrides', 'rEnemyOverrides', 'rGsLocOverrides', 'rBGMOverrides',
            'rSfxData', 'rScrubRandomItemPrices'}


def validate(seed, symbols):
    if seed['format'] != 'retuned-seed-proof-v1' or seed['runtime_ready'] is not False:
        raise ValueError('Expected development seed')
    fields = seed['runtime_fields_hex']
    if set(fields) != REQUIRED:
        raise ValueError('Unexpected or missing runtime tables')
    sizes = {}
    for name, encoded in fields.items():
        data = bytes.fromhex(encoded)
        address, capacity = symbols[name]
        if address < 0x680000 or address + capacity > 0x800000:
            raise ValueError('Runtime table outside reserved guest range')
        if name == 'rItemOverrides':
            if not data or len(data) % 8 or len(data) >= capacity:
                raise ValueError('Item table must leave room for its sentinel')
            keys = [struct.unpack_from('<I', data, offset)[0] for offset in range(0,len(data),8)]
            if keys != sorted(set(keys)) or not keys[0]:
                raise ValueError('Invalid item keys')
        elif len(data) != capacity:
            raise ValueError(f'{name}: host size {len(data)} != guest size {capacity}')
        sizes[name] = len(data)
    messages = bytes.fromhex(seed['message_data_hex'])
    entries = bytearray.fromhex(seed['message_entries_hex'])
    if not entries or len(entries) % 0x60 or max(len(messages),len(entries)) > 1024*1024:
        raise ValueError('Invalid message tables')
    base = symbols['rCustomMessages'][0]
    if base < 0x680000 or base + len(messages) + len(entries) + 3 > 0x800000:
        raise ValueError('Messages exceed reserved guest range')
    previous = -1
    for offset in range(0,len(entries),0x60):
        identifier = struct.unpack_from('<I',entries,offset)[0]
        if identifier <= previous: raise ValueError('Message IDs not ordered')
        previous = identifier
        for language in range(10):
            position = offset + 16 + language*8
            start, length = struct.unpack_from('<II',entries,position)
            if length:
                if start + length > len(messages): raise ValueError('Message outside data table')
                struct.pack_into('<I',entries,position,base+start)
    return {'runtime_ready':False, 'table_sizes':sizes, 'message_count':len(entries)//0x60,
            'relocated_entries_sha256':hashlib.sha256(entries).hexdigest(),
            'remaining':'Guest gameplay, randomized item delivery, and save/reload verification'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    helper=Path(__file__).resolve().parents[1]/'reframed/prepare_native_image.py'
    spec=importlib.util.spec_from_file_location('native_image',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    symbols={name:(address,size) for address,size,kind,name,_ in module.read_elf_symbols(a.runtime)}
    result=validate(json.loads(a.seed.read_text()),symbols)
    result['runtime_sha256']=hashlib.sha256(a.runtime.read_bytes()).hexdigest()
    result['seed_sha256']=hashlib.sha256(a.seed.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
