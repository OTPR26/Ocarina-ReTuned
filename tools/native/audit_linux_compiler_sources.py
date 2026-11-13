#!/usr/bin/env python3
"""Match bundled compiler packages to complete, checksum-verified source archives."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def fields(path):
    result = {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith('-----BEGIN PGP SIGNATURE-----'):
            break
        if line.startswith(' ') and current:
            result[current] += '\n' + line.strip()
        elif re.match(r'^[A-Za-z][A-Za-z0-9-]*:', line):
            current, value = line.split(':', 1)
            result[current] = value.strip()
        else:
            current = None
    return result


def audit(sources, manifests):
    sources = Path(sources).resolve()
    records = {}
    for path in sources.glob('*.dsc'):
        record = fields(path)
        key = (record['Source'], record['Version'])
        files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}
        entries = record['Checksums-Sha256'].strip().splitlines()
        if not entries:
            raise ValueError('No source checksums: ' + path.name)
        for line in entries:
            checksum, size, name = line.split()
            target = sources / name
            if Path(name).name != name or not target.resolve().is_relative_to(sources):
                raise ValueError('Unsafe source filename: ' + name)
            if target.stat().st_size != int(size) or hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                raise ValueError('Source checksum mismatch: ' + name)
            files[name] = checksum
        records[key] = {'source': key[0], 'version': key[1], 'files': files}
    required = set()
    for manifest in manifests:
        metadata = json.loads(Path(manifest).read_text())
        for package in metadata['packages']:
            match = re.fullmatch(r'([^\s]+)(?: \(([^)]+)\))?', package['source'])
            if match is None:
                raise ValueError('Invalid source-package reference')
            key = (match[1], match[2] or package['version'])
            if key not in records:
                raise ValueError('Missing matching source: ' + '='.join(key))
            required.add(key)
    return {'format': 'retuned_linux_toolchain_sources_v1',
            'sources': [records[key] for key in sorted(required)]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit(args.sources, args.manifest), indent=2, sort_keys=True) + '\n')
