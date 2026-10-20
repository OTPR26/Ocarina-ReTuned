"""Recursive texture discovery without copying or altering a texture pack."""
import os
from pathlib import Path

EXTENSIONS = {'.png', '.dds', '.ktx'}


def discover(folder):
    root = Path(folder).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Choose a texture folder.')
    def failed(error):
        raise OSError('A texture subfolder could not be read.') from error
    for current, directories, files in os.walk(root, followlinks=False, onerror=failed):
        directories[:] = sorted(d for d in directories if not (Path(current) / d).is_symlink())
        for name in sorted(files):
            path = Path(current) / name
            if not path.is_symlink() and path.suffix.lower() in EXTENSIONS:
                yield path.relative_to(root)
