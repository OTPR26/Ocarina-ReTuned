#!/usr/bin/env python3
"""Fetch pinned randomizer source text, excluding binaries and game resources."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

REVISION = '40703bf55b05ab2dda0933a5c5007730b05cebe2'
URL = f'https://codeload.github.com/tgacquin/oot3d-sariaui/tar.gz/{REVISION}'
PREFIX = 'externals/oot3d-randomizer/'

def fetch(output, runtime=False):
    output = Path(output)
    if output.exists():
        raise ValueError('Source destination must not already exist')
    output.mkdir(parents=True)
    files = {}
    proc = subprocess.Popen(['curl', '--fail', '--location', '--silent', '--show-error', URL], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=proc.stdout, mode='r|gz') as archive:
            for member in archive:
                parts = PurePosixPath(member.name).parts[1:]
                if not parts or '..' in parts or not member.isfile():
                    continue
                name = '/'.join(parts)
                allowed = (name.startswith(PREFIX + ('code/' if runtime else 'source/')) or name.startswith(PREFIX + 'shared/') or
                           (runtime and name.startswith('tools/oot3d/randomizer/guest_include/')) or
                           name in (PREFIX + 'LICENSE.md', PREFIX + 'UPSTREAM.txt', 'license.txt',
                                    'tools/oot3d/randomizer/host/3ds.h'))
                if not allowed or member.size > 4 * 1024 * 1024:
                    continue
                data = archive.extractfile(member).read()
                dest = output / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                files[name] = hashlib.sha256(data).hexdigest()
        if proc.wait():
            raise RuntimeError('Source download failed')
        required = 'code/src/item_override.c' if runtime else 'source/fill.cpp'
        if not (output / PREFIX / required).is_file():
            raise RuntimeError('Incomplete generator source')
        (output / 'source-receipt.json').write_text(json.dumps({'revision': REVISION, 'url': URL, 'files': files}, indent=2)+'\n')
        print(f'Fetched {len(files)} source files at {REVISION}')
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    fetch(args.output, args.runtime)
