"""Bounded, integrity-checked preparation artifacts stored only on this device."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import threading


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class LocalCache:
    def __init__(self, root, limit=512 * 1024 * 1024):
        self.root = Path(root)
        self.limit = limit
        self.lock = threading.RLock()

    def entry(self, key):
        if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Invalid preparation cache key')
        return self.root / key

    def restore(self, key, destination, expected=None, required=None):
        with self.lock:
            return self._restore(key, destination, expected, required)

    def _restore(self, key, destination, expected=None, required=None):
        if self.root.is_symlink():
            return False
        entry = self.entry(key)
        if entry.is_symlink():
            return False
        try:
            if (entry / 'receipt.json').is_symlink():
                return False
            receipt = json.loads((entry / 'receipt.json').read_text())
            if not isinstance(receipt, dict):
                return False
            files = receipt.get('files')
            if not isinstance(files, dict) or any(not isinstance(name, str) or not isinstance(value, str) for name, value in files.items()):
                return False
            if receipt.get('format') != 'retuned_preparation_cache_v1' or not files:
                return False
            if expected is not None and files != expected:
                return False
            if required is not None and set(files) != set(required):
                return False
            for name, digest in files.items():
                relative = Path(name)
                source = entry / relative
                if relative.is_absolute() or '..' in relative.parts or source.is_symlink():
                    return False
                if not source.resolve().is_relative_to(entry.resolve()) or file_hash(source) != digest:
                    return False
            destination = Path(destination)
            for name in files:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(entry / name, target)
            os.utime(entry, None)
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def store(self, key, sources):
        """A cache-write failure must never invalidate successful preparation."""
        with self.lock:
            return self._store(key, sources)

    def _store(self, key, sources):
        try:
            entry = self.entry(key)
            if self.root.is_symlink():
                return False
            self.root.mkdir(parents=True, exist_ok=True)
            if sum(Path(p).stat().st_size for p in sources.values()) > self.limit:
                return False
            with tempfile.TemporaryDirectory(prefix='.cache-', dir=self.root) as temporary:
                stage = Path(temporary) / 'entry'
                stage.mkdir()
                hashes = {}
                for name, source in sources.items():
                    relative = Path(name)
                    if relative.is_absolute() or '..' in relative.parts or name == 'receipt.json':
                        raise ValueError('Invalid preparation cache filename')
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    hashes[name] = file_hash(target)
                (stage / 'receipt.json').write_text(json.dumps({
                    'format': 'retuned_preparation_cache_v1', 'private_local_artifact': True,
                    'redistributable': False, 'files': hashes}, sort_keys=True))
                if entry.exists() or entry.is_symlink():
                    if entry.is_symlink():
                        return False
                    shutil.rmtree(entry)
                stage.rename(entry)
            self.trim()
            return True
        except OSError:
            return False

    def trim(self):
        entries = []
        for entry in self.root.iterdir():
            if entry.is_symlink() or not entry.is_dir() or len(entry.name) != 64 or any(c not in '0123456789abcdef' for c in entry.name):
                continue
            size = sum(p.stat().st_size for p in entry.rglob('*') if p.is_file() and not p.is_symlink())
            entries.append((entry.stat().st_mtime, size, entry))
        total = sum(size for _, size, _ in entries)
        for _, size, entry in sorted(entries):
            if total <= self.limit:
                break
            shutil.rmtree(entry)
            total -= size
