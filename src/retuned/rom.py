"""Inspect user-supplied decrypted cartridges without extracting game content."""
import hashlib
import json
import struct
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2] / 'resources/supported-roms.json'


def inspect(path, catalog=CATALOG):
    path = Path(path)
    if path.suffix.lower() not in {'.cci', '.3ds'}:
        raise ValueError('Select a decrypted .cci or .3ds cartridge dump.')
    entries = json.loads(Path(catalog).read_text())['roms']
    with path.open('rb') as stream:
        size = path.stat().st_size
        header = stream.read(512)
        if len(header) != 512 or header[0x100:0x104] != b'NCSD':
            raise ValueError('Invalid cartridge header.')
        offset, blocks = struct.unpack_from('<II', header, 0x120)
        base, length = offset * 512, blocks * 512
        if base < 512 or length < 1024 or base + length > size:
            raise ValueError('Invalid cartridge partition bounds.')
        stream.seek(base)
        ncch = stream.read(512)
        if ncch[0x100:0x104] != b'NCCH':
            raise ValueError('Invalid main program header.')
        if not ncch[0x18f] & 4:
            raise ValueError('Encrypted dumps are unsupported; supply a decrypted dump.')
        program = f'{struct.unpack_from("<Q", ncch, 0x118)[0]:016X}'
        candidates = [entry for entry in entries if entry['program_id'] == program]
        if not candidates:
            raise ValueError('This cartridge is not a supported Ocarina of Time 3D region.')
        stream.seek(0)
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        for entry in candidates:
            if entry['sha256'] == digest:
                return {'region': entry['region'], 'program_id': program,
                        'sha256': digest, 'verified': True}
    raise ValueError('Unverified ROM revision or modified dump; use a supported clean source.')
