#!/usr/bin/env python3
"""Stage portable Linux CMake/Ninja wheel contents with their original notices."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def stage(cmake_package, ninja_package, output):
    cmake_package, ninja_package, output = map(Path, (cmake_package, ninja_package, output))
    cmake = cmake_package / 'cmake/data'
    ninja = ninja_package / 'bin/ninja'
    if not (cmake / 'bin/cmake').is_file() or not ninja.is_file():
        raise ValueError('CMake and Ninja package contents are incomplete')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output directory for preparation tools')
    def architecture(path):
        with path.open('rb') as stream:
            header = stream.read(20)
        if header[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected a 64-bit little-endian Linux tool')
        machine = int.from_bytes(header[18:20], 'little')
        if machine not in (62, 183):
            raise ValueError('Unsupported Linux preparation-tool architecture')
        return machine
    if architecture(cmake / 'bin/cmake') != architecture(ninja):
        raise ValueError('CMake and Ninja architectures do not match')
    licenses = {}
    for name, root in (('cmake', cmake_package), ('ninja', ninja_package)):
        records = list(root.glob(name + '-*.dist-info'))
        if len(records) != 1:
            raise ValueError('Expected one installed wheel receipt for ' + name)
        record = records[0]
        notices = [p for p in record.rglob('*') if p.is_file() and
                   ('licenses' in p.parts or p.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')))]
        if not notices:
            raise ValueError('Original license texts are missing for ' + name)
        licenses[name] = (record, notices)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cmake, output / 'cmake', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('*.pfx', '*.p12'))
    (output / 'ninja').mkdir(exist_ok=True)
    shutil.copy2(ninja, output / 'ninja/ninja')
    for name, (record, notices) in licenses.items():
        destination = output / 'licenses' / name
        for path in [*notices, record / 'METADATA', record / 'WHEEL']:
            if path.is_file():
                target = destination / path.relative_to(record)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'tools-manifest.json'}
    (output / 'tools-manifest.json').write_text(json.dumps({'schema': 1, 'files': files}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake-package', 'ninja-package', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.cmake_package, args.ninja_package, args.output)
