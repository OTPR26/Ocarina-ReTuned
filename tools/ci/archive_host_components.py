#!/usr/bin/env python3
"""Fail closed before uploading a narrow host-component directory."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = ('.3ds', '.cci', '.cia', '.romfs', '.sav', '.state', '.jks',
                      '.keystore', '.p12', '.mobileprovision', '.pem', '.key')
FORBIDDEN_NAMES = ('privategame', '_codesignature', 'whole_aot_shard_',
                   'oot3d_translated_vertex_programs.h', 'oot3d_native_vertex.spvpack',
                   'native-launch.json', 'savegame', 'zelda.sav')


def check_file(path, root):
    name = path.relative_to(root).as_posix()
    lower = name.lower()
    if path.is_symlink() or lower.endswith(FORBIDDEN_SUFFIXES) or any(x in lower for x in FORBIDDEN_NAMES):
        raise ValueError('Unexpected host artifact: ' + name)
    data = path.read_bytes()
    for marker in (b'/Users/', b'C:\\Users\\', b'/home/runner/', b'/__w/', b'/github/workspace/',
                   b'-----BEGIN PRIVATE KEY-----', b'-----BEGIN RSA PRIVATE KEY-----'):
        if marker in data:
            raise ValueError('Unmapped build path or signing material in: ' + name)
    return {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('platform', choices=('ios', 'tvos', 'windows-arm64', 'switch'))
    args = p.parse_args()
    root = ROOT / 'artifacts/host-components'
    records = [check_file(path, root) for path in sorted(root.rglob('*')) if path.is_file()]
    if len(records) < 2:
        raise ValueError('No host components to upload')
    (root / 'inventory.json').write_text(json.dumps(records, indent=2) + '\n')
    archive = root.parent / ('Ocarina-ReTuned-Host-' + args.platform + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                output.write(path, path.relative_to(root))
    sys.path.insert(0, str(ROOT / 'tools/native'))
    from audit_release_assets import audit
    result = audit([archive])
    if result['findings']:
        archive.unlink()
        raise ValueError('Host asset audit failed')


if __name__ == '__main__':
    main()
