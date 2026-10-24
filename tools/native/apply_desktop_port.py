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
    # A cross-build runs the dependency manager on the build machine.
    automate = root / 'CMake/automate-vcpkg.cmake'
    source = automate.read_text()
    before = '    if(WIN32)\n        set(VCPKG_EXEC ${VCPKG_ROOT}/vcpkg.exe)'
    after = before.replace('if(WIN32)', 'if(CMAKE_HOST_WIN32)')
    if after not in source:
        if source.count(before) != 1:
            raise ValueError('Dependency-manager host selection context changed')
        automate.write_text(source.replace(before, after))
    # Windows needs extension entry points loaded through GLEW with either driver.
    gl_header = root / 'runtime/three_ds_recomp/include/fast/backends/gfx_opengl.h'
    source = gl_header.read_text()
    before = '#ifdef _MSC_VER\n#include <SDL2/SDL.h>'
    after = '#if defined(_WIN32)\n#include <SDL2/SDL.h>'
    if after not in source:
        if source.count(before) != 1:
            raise ValueError('Windows OpenGL loader context changed')
        gl_header.write_text(source.replace(before, after))
    entry = root / 'tools/oot3d/native_game_runtime/oot3d_native_game.cpp'
    source = entry.read_text()
    before = '#if defined(__SWITCH__) || defined(__ANDROID__)\n#include <SDL.h>'
    after = '#if defined(__SWITCH__) || defined(__ANDROID__) || defined(_WIN32)\n#include <SDL.h>'
    if after not in source:
        if source.count(before) != 1:
            raise ValueError('Windows SDL entry context changed')
        entry.write_text(source.replace(before, after))
    dependencies = root / 'runtime/three_ds_recomp/cmake/dependencies/windows.cmake'
    source = dependencies.read_text()
    addition = '\nif(MINGW)\n    target_link_libraries(ImGui PUBLIC ksuser)\nendif()\n'
    if addition not in source:
        dependencies.write_text(source + addition)
    if portable_windows:
        cmake = root / 'CMakeLists.txt'
        source = cmake.read_text()
        for architecture, indent in (('x64', '    '), ('arm64', '        ')):
            before = f'{indent}set(VCPKG_TRIPLET {architecture}-windows-static)\n{indent}set(VCPKG_TARGET_TRIPLET {architecture}-windows-static)'
            after = before.replace('-windows-static', '-mingw-static')
            if after not in source:
                if source.count(before) != 1:
                    raise ValueError('Windows dependency triplet context changed: ' + architecture)
                source = source.replace(before, after)
        cmake.write_text(source)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--portable-windows', action='store_true')
    args = parser.parse_args()
    apply(args.engine, args.portable_windows)
