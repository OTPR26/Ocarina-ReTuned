#!/usr/bin/env python3
"""Apply the shared frontend to the pinned Windows/Linux neutral host."""
import argparse
from pathlib import Path
import subprocess
from apply_common_port import apply as common

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'

def apply_windows_link_options(root):
    """Use MSVC linker switches only with the MSVC-compatible driver."""
    path = Path(root) / 'CMake/oot3d/game.cmake'
    source = path.read_text()
    for before, after in (
        ('if (CMAKE_SYSTEM_NAME STREQUAL "Windows" AND NOT OOT3D_FAST_DEV_LINK)',
         'if (MSVC AND CMAKE_SYSTEM_NAME STREQUAL "Windows" AND NOT OOT3D_FAST_DEV_LINK)'),
        ('elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")',
         'elseif(MSVC AND CMAKE_SYSTEM_NAME STREQUAL "Windows")'),
    ):
        if after in source:
            continue
        if source.count(before) != 1:
            raise ValueError('Windows linker option context changed')
        source = source.replace(before, after)
    path.write_text(source)


def apply(root, portable_windows=False):
    root = Path(root)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Unexpected runtime revision')
    common(root)
    apply_windows_link_options(root)
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
