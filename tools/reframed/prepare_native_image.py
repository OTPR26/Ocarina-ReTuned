#!/usr/bin/env python3
"""Prepare a private native title image from an audited base and Reframed ELF/IPS.

No game bytes are built into this tool. The output must stay on the user's
machine. The native process maps the mod's segment, replacing only its console
permission setup; all HUD, menu and camera functions remain the original mod.
"""
import argparse
import csv
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

BASE_SHA256 = '16a6b0aa4c4784680220a6f780f7f8a73cfb205557aa9f9f0e705179e0613220'
BASE = 0x100000
INJECTION = 0x5C7000


def apply_ips(base, patch):
    if not patch.startswith(b'PATCH'):
        raise ValueError('Invalid IPS header')
    data = bytearray(base)
    position = 5
    intervals = []
    while patch[position:position + 3] != b'EOF':
        if position + 5 > len(patch):
            raise ValueError('Truncated IPS record')
        offset = int.from_bytes(patch[position:position + 3], 'big')
        length = int.from_bytes(patch[position + 3:position + 5], 'big')
        position += 5
        if length:
            payload = patch[position:position + length]
            if len(payload) != length:
                raise ValueError('Truncated IPS payload')
            position += length
        else:
            if position + 3 > len(patch):
                raise ValueError('Truncated IPS run')
            length = int.from_bytes(patch[position:position + 2], 'big')
            payload = patch[position + 2:position + 3] * length
            position += 3
        if offset + length > 0x600000:
            raise ValueError('Patch exceeds native prototype image limit')
        if offset + length > len(data):
            data.extend(b'\0' * (offset + length - len(data)))
        data[offset:offset + length] = payload
        intervals.append((offset + BASE, length))
    if position + 3 != len(patch):
        raise ValueError('Unexpected IPS trailer')
    return data, intervals



def adjusted_return_sites(image, intervals, functions):
    adjustments = {}
    for function in functions:
        if not function['name'].startswith('hook'):
            continue
        deltas = set()
        for address in range(function['entry'], function['entry'] + function['size'], 4):
            raw = struct.unpack_from('<I', image, address - BASE)[0]
            if raw & 0x0E0FF000 != 0x020EE000:
                continue
            operation = (raw >> 21) & 15
            if operation not in (2, 4):
                continue
            rotate = ((raw >> 8) & 15) * 2
            value = raw & 255
            value = ((value >> rotate) | (value << ((32 - rotate) % 32))) & 0xFFFFFFFF
            deltas.add(value if operation == 4 else -value)
        if deltas:
            adjustments[function['entry']] = deltas
    sites = set()
    for start, size in intervals:
        for address in range((start + 3) & ~3, min(start + size, INJECTION), 4):
            raw = struct.unpack_from('<I', image, address - BASE)[0]
            if raw & 0x0F000000 != 0x0B000000 or raw >> 28 == 15:
                continue
            relative = raw & 0xFFFFFF
            if relative & 0x800000:
                relative -= 0x1000000
            target = address + 8 + relative * 4
            for delta in adjustments.get(target, ()):
                resume = address + 4 + delta
                if resume % 4 or not BASE <= resume < INJECTION:
                    raise ValueError('Invalid adjusted native return')
                sites.add(resume)
    return sorted(sites)


def read_elf_symbols(elf):
    """Read ARM ELF32 symbols without an external executable (also Android)."""
    data = Path(elf).read_bytes()
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H', data, 18)[0] != 40:
        raise ValueError('Expected a little-endian ARM ELF32 mod')
    offset = struct.unpack_from('<I', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 46)
    if size != 40 or not count or offset + size * count > len(data):
        raise ValueError('Invalid ELF section table')
    sections = [struct.unpack_from('<10I', data, offset + i * size) for i in range(count)]
    def contents(section):
        start, length = section[4:6]
        if start + length > len(data):
            raise ValueError('ELF section is outside file')
        return data[start:start + length]
    symbols = []
    kinds = {0: 'NOTYPE', 1: 'OBJECT', 2: 'FUNC'}
    for section in sections:
        if section[1] != 2:
            continue
        if section[6] >= count or section[9] != 16 or section[5] % 16:
            raise ValueError('Invalid ELF symbol table')
        names = contents(sections[section[6]])
        table = contents(section)
        for index in range(0, section[5], 16):
            name, address, length, info, other, section_index = struct.unpack_from('<IIIBBH', table, index)
            if not 0 < section_index < count or (info & 15) not in kinds:
                continue
            if name >= len(names) or names.find(b'\0', name) < 0:
                raise ValueError('Invalid ELF symbol name')
            label = names[name:names.index(b'\0', name)].decode('utf-8')
            symbols.append((address, length, kinds[info & 15], label, str(section_index)))
    if not symbols:
        raise ValueError('Mod ELF has no usable symbols')
    return symbols


def elf_symbols(readelf, elf):
    symbols = read_elf_symbols(elf)
    mappings = {}
    for address, _, _, name, section in symbols:
        if name.startswith(('$a', '$t', '$d')):
            mappings.setdefault(section, []).append((address, name[1]))
    for values in mappings.values():
        values.sort()
    def is_arm(symbol):
        address, _, kind, _, section = symbol
        active = [mode for start, mode in mappings.get(section, []) if start <= address]
        return bool(active) and active[-1] == 'a'
    eligible = [symbol for symbol in symbols if symbol[2] == 'FUNC' or
        (symbol[2] == 'NOTYPE' and not symbol[3].startswith(('$', '__')) or symbol[3] == '__text_end')]
    return [symbol for symbol in eligible if is_arm(symbol) or symbol[3] == '__text_end']


def touch_action_owner(image, entry):
    # Resolve the global owner referenced by our own mod's action adapter.
    # Require the literal-load/dereference pair, rather than a ROM address.
    candidates=[]
    for pc in range(entry, entry+64, 4):
        word, following=struct.unpack_from('<II',image,pc-BASE)
        if word & 0xFFFFF000 == 0xE59F3000 and following == 0xE5933000:
            literal=pc+8+(word&0xFFF)
            if entry<=literal<len(image)+BASE-4:
                candidates.append(struct.unpack_from('<I',image,literal-BASE)[0])
    if len(candidates)!=1:
        raise ValueError('Unknown native action-owner adapter')
    return candidates[0]


def _prepare(args):
    if args.output.exists():
        raise ValueError('Refusing to replace a private title experiment')
    base = args.code.read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA256:
        raise ValueError('Expected the verified canonical game input')
    image, intervals = apply_ips(base, args.ips.read_bytes())
    symbols = elf_symbols(args.readelf, args.elf)
    named = {name: (address, size, kind, section) for address, size, kind, name, section in symbols}
    loader, loader_size, _, loader_section = named['loader_main']
    initialize, _, _, _ = named['NativeHud_InitializeScale']
    # The host maps the extra image segment. Do not invoke Luma's SVC 0x70.
    branch = initialize - (loader + 4 + 8)
    if branch % 4 or not -(1 << 25) <= branch < (1 << 25) or loader_size < 12:
        raise ValueError('Invalid native loader adaptation')
    replacement = struct.pack('<III', 0xE92D4010, 0xEB000000 | ((branch >> 2) & 0xFFFFFF), 0xE8BD8010)
    image[loader - BASE:loader - BASE + 12] = replacement
    frontend = None
    if getattr(args, 'native_frontend', False):
        if not getattr(args, 'save_context', None):
            raise ValueError('Native frontend requires a verified save-context address')
        adapters = {
            'MenuPreferences_Update': (0xE12FFF1E,),
            'MenuPreferences_Save': (0xE3A00001, 0xE12FFF1E),
            'MenuOptions_Begin': (0xEF00007E, 0xE12FFF1E),
            'MenuOptions_Update': (0xE3A00000, 0xE12FFF1E),
            'MenuOptions_Touch': (0xE3A00000, 0xE12FFF1E),
            'MenuOptions_Draw': (0xE12FFF1E,),
        }
        for name, words in adapters.items():
            address, length, _, _ = named[name]
            if length < len(words)*4:
                raise ValueError('Frontend adapter exceeds function: ' + name)
            image[address-BASE:address-BASE+len(words)*4] = struct.pack('<'+'I'*len(words), *words)
        object_symbols = {}
        for address, _, _, name, _ in read_elf_symbols(args.elf):
            if name in ('gSaveContext','gGlobalContext','gNativeHudPositions','gNativeHudUVs','sNativeHudPauseLayout','sNativeHudOcarinaLayout','sNativeActionSource'):
                object_symbols[name] = address
        functions = ('NativeHud_GetScalePercent','NativeHud_SetScalePercent',
            'Camera_GetDistanceOption','Camera_SetDistanceOption','Camera_GetControlMode',
            'Camera_SetControlMode','MovementOptions_Get','MovementOptions_Set',
            'InputRemap_IsOcarinaUiOpen','InputRemap_IsOcarinaUiReady','InputRemap_CloseOcarinaUi')
        frontend = {'schema':1,'context_pointer':object_symbols['gGlobalContext'],
            'save_context':args.save_context,'functions':{name:named[name][0] for name in functions},
            'touch_hud':{'upload_positions':named['NativeHud_UploadPositions'][0],
                'prepare_action':named['NativeHud_PrepareActionPrompt'][0],
                'positions':object_symbols['gNativeHudPositions'],
                'uvs':object_symbols['gNativeHudUVs'],
                'pause_layout':object_symbols['sNativeHudPauseLayout'],
                'ocarina_layout':object_symbols['sNativeHudOcarinaLayout'],
                'action_source':object_symbols['sNativeActionSource'],
                'action_owner':touch_action_owner(image,named['NativeHud_PrepareActionPrompt'][0])}}
    out = args.output
    out.mkdir(parents=True)
    (out / 'code.bin').write_bytes(image)
    with args.inventory.open(newline='') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        rows = list(reader)
    known = {int(row['entry'], 0) for row in rows}
    eligible = [s for s in symbols if s[0] >= INJECTION or s[4] == loader_section]
    additions = []
    for address, size, kind, name, section in sorted(eligible, key=lambda s: (s[0], s[2] != 'FUNC', s[3])):
        if name == '__text_end' or address in known:
            continue
        if size == 0:
            following = min((a for a, _, _, _, sec in eligible if sec == section and a > address), default=None)
            if following is not None:
                size = following - address
            else:
                # GNU assembly SVC wrappers omit ELF sizes. Bound the final
                # wrapper by its explicit return, never by another section.
                for end in range(address, min(address + 256, BASE + len(image)), 4):
                    if struct.unpack_from('<I', image, end - BASE)[0] == 0xE12FFF1E:
                        size = end + 4 - address
                        break
                if not size:
                    raise ValueError('Unbounded assembly symbol: ' + name)
        if address % 4 or size % 4 or not size or address + size > BASE + len(image):
            raise ValueError('Invalid executable symbol: ' + name)
        if name == 'loader_main':
            size = 12
        row = dict.fromkeys(fields, '')
        row.update(profile='reframed_eur', entry=hex(address), end=hex(address + size - 1),
                   size=str(size), name='reframed_' + name, memory_block='reframed_text')
        rows.append(row)
        known.add(address)
        additions.append({'entry': address, 'size': size, 'name': name})
    resumes = adjusted_return_sites(image, intervals, additions)
    (out / 'observed-sites.json').write_text(json.dumps({
        'format': 'oot3d_whole_aot_observed_sites_v1',
        'code_sha256': hashlib.sha256(image).hexdigest(),
        'sites': [{'pc': hex(pc), 'reason': 'mod-adjusted return'} for pc in resumes]
    }, indent=2) + '\n')
    rows.sort(key=lambda row: int(row['entry'], 0))
    with (out / 'inventory.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = json.loads(args.manifest.read_text())
    if frontend is not None:
        manifest['reframed_frontend'] = frontend
    manifest['source'].update(code_bin_path=str((out / 'code.bin').resolve()),
                              code_bin_sha256=hashlib.sha256(image).hexdigest(), code_bin_size=len(image))
    size = len(image) - (INJECTION - BASE)
    if size <= 0:
        raise ValueError('Missing injected mod image')
    for segment in manifest['process']['segments']:
        if segment['address'] + segment['mapped_size'] > INJECTION:
            declared_end = segment['address'] + segment['declared_code_size']
            if segment['name'] == 'data_bss':
                declared_end += manifest['process']['bss_declared_size']
            if declared_end > INJECTION or segment['address'] + segment['file_size'] > INJECTION:
                raise ValueError('Injected mod overlaps declared game data')
            # Split unused page padding; preserve all declared data and BSS.
            segment['mapped_size'] = INJECTION - segment['address']
    manifest['process']['segments'].append({'name': 'reframed', 'address': INJECTION,
        'mapped_size': (size + 4095) & ~4095, 'declared_code_size': size,
        'file_offset': INJECTION - BASE, 'file_size': size, 'writable': True, 'executable': True})
    (out / 'process-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'schema': 1, 'private_local_artifact': True, 'redistributable': False,
        'base_sha256': BASE_SHA256, 'mod_ips_sha256': hashlib.sha256(args.ips.read_bytes()).hexdigest(),
        'code_sha256': hashlib.sha256(image).hexdigest(), 'patch_records': len(intervals),
        'added_functions': additions, 'native_loader': {'address': loader, 'bytes': 12}}
    (out / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def prepare(args):
    destination = args.output
    if destination.exists():
        raise ValueError('Refusing to replace a private title experiment')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.reframed-image-', dir=destination.parent) as temporary:
        staged = copy.copy(args)
        staged.output = Path(temporary) / 'image'
        receipt = _prepare(staged)
        # The manifest must reference the final image, not the temporary path.
        manifest = staged.output / 'process-manifest.json'
        document = json.loads(manifest.read_text())
        document['source']['code_bin_path'] = str((destination / 'code.bin').resolve())
        manifest.write_text(json.dumps(document, indent=2) + '\n')
        staged.output.rename(destination)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('code', 'ips', 'elf', 'inventory', 'manifest', 'readelf', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--native-frontend', action='store_true')
    parser.add_argument('--save-context', type=lambda value: int(value, 0))
    result = prepare(parser.parse_args())
    print(f"Prepared private mod image: {result['patch_records']} patches, {len(result['added_functions'])} mod entries")
