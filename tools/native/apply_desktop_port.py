#!/usr/bin/env python3
"""Apply the shared frontend to the pinned Windows/Linux neutral host."""
import argparse
from pathlib import Path
import subprocess
from apply_common_port import apply as common

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'

def apply(root, portable_windows=False):
    root = Path(root)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Unexpected runtime revision')
    common(root)
    if portable_windows:
        cmake = root / 'CMakeLists.txt'
        source = cmake.read_text()
        before = '    set(VCPKG_TRIPLET x64-windows-static)\n    set(VCPKG_TARGET_TRIPLET x64-windows-static)'
        after = '    set(VCPKG_TRIPLET x64-mingw-static)\n    set(VCPKG_TARGET_TRIPLET x64-mingw-static)'
        if after not in source:
            if source.count(before) != 1:
                raise ValueError('Windows dependency triplet context changed')
            cmake.write_text(source.replace(before, after))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--portable-windows', action='store_true')
    args = parser.parse_args()
    apply(args.engine, args.portable_windows)
