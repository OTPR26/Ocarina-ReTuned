#!/usr/bin/env python3
"""Keep CTest registration rooted in the engine when Android embeds it."""
import argparse
from pathlib import Path
import subprocess
from apply_common_port import apply as apply_common

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'


def apply(root):
    root = Path(root)
    if subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() != REVISION:
        raise ValueError('Unexpected native runtime revision.')
    apply_common(root)
    window=root/'runtime/three_ds_recomp/src/fast/backends/gfx_sdl2.cpp'
    def mobile_window(before,after):
        value=window.read_text()
        if after in value:return
        if value.count(before)!=1:raise ValueError('Android window context changed')
        window.write_text(value.replace(before,after))
    mobile_window('void GfxWindowBackendSDL2::SetFullscreenImpl(bool on, bool call_callback) {',
                  'void GfxWindowBackendSDL2::SetFullscreenImpl(bool on, bool call_callback) {\n#ifdef __ANDROID__\n    on=true;\n#endif')
    mobile_window('    Uint32 flags = SDL_WINDOW_BORDERLESS | SDL_WINDOW_SHOWN;',
                  '    Uint32 flags = SDL_WINDOW_BORDERLESS | SDL_WINDOW_SHOWN;\n#ifdef __ANDROID__\n    flags |= SDL_WINDOW_FULLSCREEN;\n#endif')
    path = root / 'CMake/oot3d/tests.cmake'
    source = path.read_text()
    if source.count('${CMAKE_CURRENT_SOURCE_DIR}') == 3:
        return
    if source.count('${CMAKE_SOURCE_DIR}') != 3:
        raise ValueError('Native test-registration context changed.')
    path.write_text(source.replace('${CMAKE_SOURCE_DIR}', '${CMAKE_CURRENT_SOURCE_DIR}'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
