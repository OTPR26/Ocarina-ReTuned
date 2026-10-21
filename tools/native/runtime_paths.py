"""Reject build-machine paths before neutral binaries are archived."""
from pathlib import Path


def verify_runtime_paths(binaries, roots):
    needles = set()
    for root in roots:
        text = str(root)
        if len(text) < 4:
            raise ValueError('Runtime privacy scan needs explicit build roots')
        for variant in (text, text.replace('\\', '/'), text.replace('/', '\\')):
            for encoding in ('utf-8', 'utf-16-le'):
                needles.add(variant.encode(encoding).lower())
    if not needles:
        raise ValueError('Runtime privacy scan needs explicit build roots')
    for binary in binaries:
        data = Path(binary).read_bytes().lower()
        if any(needle in data for needle in needles):
            raise ValueError('Local build path survived in runtime binary: ' + Path(binary).name)
