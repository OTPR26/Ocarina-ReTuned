#!/usr/bin/env python3
"""Build a bundled UI pack from an explicitly supplied, pinned release archive.

Run locally during packaging. This does not download or publish any resources.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

from prepare_ui_assets import CONTRACT, read_pack


def stage(source, destination):
    source, destination = Path(source), Path(destination)
    contract = json.loads(CONTRACT.read_text())
    if (source.is_symlink() or source.stat().st_size != contract['source_bytes'] or
            hashlib.sha256(source.read_bytes()).hexdigest() != contract['source_sha256']):
        raise ValueError('Expected the pinned Reframed release archive')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Refusing to overwrite a UI pack')
    selected = {contract['source_prefix'] + name: ('romfs/' + name, info)
                for name, info in contract['resources'].items()}
    selected.update({name: (name, info) for name, info in contract['notices'].items()})
    payloads = {}
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate source archive entries')
        for name, (output, expected) in selected.items():
            entry = archive.getinfo(name)
            if (entry.file_size != expected['bytes'] or entry.flag_bits & 1 or
                    stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Invalid source resource entry')
            data = archive.read(entry)
            if hashlib.sha256(data).hexdigest() != expected['sha256']:
                raise ValueError('Source resource hash mismatch')
            payloads[output] = data
    temporary = destination.with_name(destination.name + '.partial')
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name, data in sorted(payloads.items()):
                    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, data)
        read_pack(temporary)
        temporary.replace(destination)
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
    return {'bytes': destination.stat().st_size,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'resources': len(contract['resources']), 'notices': len(contract['notices'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.source, args.output), indent=2))
