"""Validate and install user-supplied Android Vulkan driver archives."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_FILES = 64


def _sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def install(archive, destination, android_api):
    archive, destination = Path(archive), Path(destination)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Driver archive exceeds 128 MiB.')
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError("Driver storage must be a private directory.")
    target = destination / digest
    if target.is_symlink():
        raise ValueError("Invalid driver storage.")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if not entries or len(entries) > MAX_FILES:
            raise ValueError('Invalid number of driver files.')
        names = set()
        total = 0
        for entry in entries:
            name = entry.filename
            mode = entry.external_attr >> 16
            if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name)
                    or name in names or name == 'selection.json' or entry.is_dir()
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or stat.S_ISLNK(mode) or entry.flag_bits & 1):
                raise ValueError('Driver packages must contain unique, regular files at the archive root.')
            names.add(name)
            total += entry.file_size
            if total > MAX_EXPANDED_BYTES:
                raise ValueError('Expanded driver exceeds 256 MiB.')
        if 'meta.json' not in names or package.getinfo('meta.json').file_size > 16384:
            raise ValueError('Driver metadata is missing or too large.')
        metadata = json.loads(package.read('meta.json'))
        if not isinstance(metadata, dict) or type(metadata.get('schemaVersion')) is not int or metadata.get('schemaVersion') != 1:
            raise ValueError('Unsupported driver metadata version.')
        library = metadata.get('libraryName', '')
        if not isinstance(library, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.so', library) or library not in names:
            raise ValueError('Driver library is missing or invalid.')
        minimum = metadata.get('minApi')
        if type(minimum) is not int or minimum < 1 or minimum > android_api:
            raise ValueError('Driver requires a different Android version.')
        with tempfile.TemporaryDirectory(prefix='.import-', dir=destination) as temporary:
            stage = Path(temporary)
            for entry in entries:
                with package.open(entry) as source, (stage / entry.filename).open('xb') as output:
                    copied = 0
                    while chunk := source.read(1024 * 1024):
                        copied += len(chunk)
                        if copied > entry.file_size:
                            raise ValueError('Driver file exceeds declared size.')
                        output.write(chunk)
                    if copied != entry.file_size:
                        raise ValueError('Incomplete driver file.')
            with (stage / library).open('rb') as source:
                header = source.read(64)
            if (len(header) < 64 or header[:6] != b'\x7fELF\x02\x01'
                    or int.from_bytes(header[16:18], 'little') != 3
                    or int.from_bytes(header[18:20], 'little') != 183):
                raise ValueError('Driver must be an ARM64 Android shared library.')
            if target.exists():
                for entry in entries:
                    existing = target / entry.filename
                    if existing.is_symlink() or not existing.is_file() or _sha256(existing) != _sha256(stage / entry.filename):
                        raise ValueError('Previously imported driver is damaged. Remove it before importing again.')
            else:
                os.rename(stage, target)
    return {'id': digest, 'library': library, 'name': str(metadata.get('name', 'Custom driver'))[:128]}


def install_json(archive, destination, android_api):
    return json.dumps(install(archive, destination, android_api))
