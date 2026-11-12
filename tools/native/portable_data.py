#!/usr/bin/env python3
"""Copy and relocate Windows portable game data without modifying AppData."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

MARKER = 'portable.json'
FORMAT = 'retuned_portable_data_v1'


def write_json(path, value):
    temporary = path.with_name(path.name + '.portable-new')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def files(root):
    def inaccessible(error):
        raise error
    for directory, folders, names in os.walk(root, followlinks=False, onerror=inaccessible):
        for name in folders + names:
            path = Path(directory) / name
            if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('Linked folders/files cannot be migrated: ' + str(path))
            if path.is_file():
                yield path
            elif not path.is_dir():
                raise ValueError('Unsupported file: ' + str(path))


def inventory(root):
    result = {}
    for path in files(root):
        with path.open('rb') as stream:
            result[path.relative_to(root).as_posix()] = (
                path.stat().st_size, hashlib.file_digest(stream, 'sha256').hexdigest())
    return result


def remap(value, mappings):
    if isinstance(value, dict):
        return {key: remap(item, mappings) for key, item in value.items()}
    if isinstance(value, list):
        return [remap(item, mappings) for item in value]
    if isinstance(value, str):
        # Match whole path components, including Windows paths when tested on Mac.
        normalized = value.replace('\\', '/').rstrip('/')
        for old, new in mappings:
            old = str(old).replace('\\', '/').rstrip('/')
            casefold = len(old) > 1 and old[1] == ':'
            compare, prefix = (normalized.casefold(), old.casefold()) if casefold else (normalized, old)
            if compare == prefix or compare.startswith(prefix + '/'):
                return str(new).replace('\\', '/').rstrip('/') + normalized[len(old):]
    return value


def rebase(root, mappings):
    # Runtime paths are JSON values. Binary saves, models, and title modules stay byte-identical.
    for path in sorted(root.rglob('*.json')):
        if path.name == MARKER:
            continue
        try:
            original = json.loads(path.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError):
            continue  # Logs and unrelated user files are not migration metadata.
        updated = remap(original, mappings)
        if updated != original:
            write_json(path, updated)


def marker(root, app):
    return {'format': FORMAT, 'data_root': str(root), 'app_root': str(app)}


def migrate(source, app):
    source_alias = source.absolute()
    source, app = source.resolve(), app.resolve()
    destination = app / 'user'
    if not source.is_dir() or not (source / 'native-launch.json').is_file():
        raise ValueError('Prepare your game before enabling portable mode.')
    if destination.exists() or destination.is_symlink():
        raise ValueError('The user folder already exists. Nothing was replaced.')
    if app == source or source in app.parents or app in source.parents:
        raise ValueError('The app and source data folders must be separate.')
    before = inventory(source)
    required = sum(size for size, _ in before.values())
    if shutil.disk_usage(app).free < required + 64 * 1024 * 1024:
        raise ValueError('Not enough free space beside the app for a verified copy.')
    stage = Path(tempfile.mkdtemp(prefix='.portable-copy-', dir=app))
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True, symlinks=True)
        if inventory(stage) != before or inventory(source) != before:
            raise ValueError('Game data changed during copying. Close other app instances and retry.')
        rebase(stage, [(source, destination), (source_alias, destination)])
        write_json(stage / MARKER, marker(destination, app))
        # Windows rename does not replace an existing directory.
        if destination.exists():
            raise ValueError('The user folder appeared during copying. Nothing was replaced.')
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination


def relocate(app):
    app = app.resolve()
    root = app / 'user'
    metadata = json.loads((root / MARKER).read_text(encoding='utf-8'))
    if metadata.get('format') != FORMAT:
        raise ValueError('Unsupported portable data format.')
    old_data, old_app = metadata['data_root'], metadata['app_root']
    if metadata == marker(root, app):
        return root
    # Keep the old marker until all replacements finish. An interrupted relocation
    # is idempotent: the next launch completes any remaining old-path replacements.
    list(files(root))  # Reject links before changing any paths, without hashing game assets.
    for temporary in root.rglob('*.json.portable-new'):
        temporary.unlink()
    rebase(root, [(old_data, root), (old_app, app)])
    write_json(root / MARKER, marker(root, app))
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    try:
        migrate(args.source, args.app) if args.source else relocate(args.app)
    except (OSError, ValueError) as error:
        print(str(error))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
