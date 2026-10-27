#!/usr/bin/env python3
"""Stage pinned NumPy wheels in a bundled desktop preparation runtime."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import zipfile

CONTRACT = Path(__file__).with_name('player_models') / 'numpy_runtime.json'


def stage(python, platform, cache):
    python, cache = Path(python), Path(cache)
    record = json.loads(CONTRACT.read_text())['platforms'][platform]
    windows = platform.startswith('windows')
    library = python / ('Lib' if windows else 'lib/python3.12')
    if not library.is_dir():
        raise ValueError('The model runtime requires bundled Python 3.12')
    cache.mkdir(parents=True, exist_ok=True)
    wheel = cache / record['filename']
    if not wheel.exists():
        pending = wheel.with_suffix('.pending')
        try:
            subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                            record['url'], '--output', str(pending)], check=True)
            if pending.stat().st_size != record['bytes'] or hashlib.sha256(pending.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('NumPy download integrity check failed')
            pending.replace(wheel)
        finally:
            pending.unlink(missing_ok=True)
    if wheel.stat().st_size != record['bytes'] or hashlib.sha256(wheel.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Cached NumPy integrity check failed')
    target = library / 'site-packages'
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        total = 0
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            total += entry.file_size
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or
                    entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr >> 16) or total > 128 * 1024**2):
                raise ValueError('Invalid NumPy wheel entry')
            if entry.is_dir():
                continue
            if not (path.parts[0] in ('numpy', 'numpy.libs') or path.parts[0] == 'numpy-2.3.2.dist-info'):
                continue
            output = target.joinpath(*path.parts)
            if output.is_symlink() or any(p.is_symlink() for p in output.parents if p != target.parent):
                raise ValueError('Linked NumPy output path')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(archive.read(entry))
            output.chmod(0o755 if entry.external_attr >> 16 & 0o111 else 0o644)
    notices = target / 'numpy-2.3.2.dist-info/LICENSE.txt'
    if not notices.is_file() or notices.stat().st_size < 1000:
        raise ValueError('NumPy component license notices are missing')
    return {'platform': platform, 'version': '2.3.2', 'sha256': record['sha256'], 'original_notices_retained': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--platform', choices=json.loads(CONTRACT.read_text())['platforms'], required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.python, args.platform, args.cache)))
