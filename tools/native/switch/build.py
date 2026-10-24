#!/usr/bin/env python3
"""Build a private Switch NRO locally with devkitPro; never dispatch CI.

Generated sources and the resulting playable NRO contain user game code.
They must not be uploaded as public release assets.
"""
import argparse
import os
from pathlib import Path
import subprocess
from apply_switch_port import apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk', 'engine', 'generated', 'json-include', 'work-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--renderer', choices=('opengl', 'deko3d'), default='opengl',
                        help='deko3d is experimental and requires isolated source trees')
    parser.add_argument('--deko-sdl-source', type=Path)
    parser.add_argument('--deko-uam-source', type=Path)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if args.renderer == 'deko3d':
        if not args.deko_sdl_source or not args.deko_uam_source:
            parser.error('deko3d requires --deko-sdl-source and --deko-uam-source')
        for root, relative in ((args.deko_sdl_source, 'src/video/switch/SDL_switchvideo.c'),
                               (args.deko_uam_source, 'uam_api.h')):
            if not (root / relative).is_file():
                parser.error('A required local deko3d source is missing: ' + relative)
    # GCC specs do not accept spaces in the SDK root. A stable symlink is fine.
    sdk = args.sdk.absolute()
    if ' ' in str(sdk):
        parser.error('Use a space-free SDK path or symlink')
    engine = args.engine.resolve()
    generated = args.generated.resolve()
    work = args.work_dir.resolve()
    for path in (sdk / 'cmake/Switch.cmake', sdk / 'devkitA64/bin/aarch64-none-elf-g++',
                 args.json_include / 'nlohmann/json.hpp', generated / 'whole_aot_cpp_manifest.json'):
        if not path.is_file():
            parser.error('A required local build input is missing: ' + path.name)
    env = dict(os.environ, DEVKITPRO=str(sdk), DEVKITA64=str(sdk / 'devkitA64'))
    env['PATH'] = str(sdk / 'tools/bin') + os.pathsep + env['PATH']
    def run(*command):
        subprocess.run([str(x) for x in command], env=env, check=True)
    source = Path(__file__).resolve().parent
    apply(engine)
    renderer_options = ['-DRETUNED_SWITCH_DEKO=OFF']
    if args.renderer == 'deko3d':
        from deko_backend.apply import apply as apply_deko
        from deko_backend.build_uam import build as build_uam
        apply_deko(engine, args.deko_sdl_source, sdk)
        compiler_build = work / 'uam-build'
        build_uam(args.deko_uam_source, compiler_build, sdk)
        renderer_options = [
            '-DRETUNED_SWITCH_DEKO=ON',
            '-DRETUNED_SDL_SOURCE=' + str(args.deko_sdl_source.resolve()),
            '-DRETUNED_UAM_SOURCE=' + str(args.deko_uam_source.resolve()),
            '-DRETUNED_UAM_LIBRARY=' + str(compiler_build / 'libretuned_uam.a'),
        ]
    run('cmake', '-S', source, '-B', work / 'title-build', '-G', 'Ninja',
        '-DCMAKE_TOOLCHAIN_FILE=' + str(sdk / 'cmake/Switch.cmake'),
        '-DRETUNED_ENGINE=' + str(engine), '-DRETUNED_GENERATED=' + str(generated),
        '-DRETUNED_JSON_INCLUDE=' + str(args.json_include.resolve()))
    run('cmake', '--build', work / 'title-build', '--parallel', args.jobs)
    run('cmake', '-S', engine, '-B', work / 'host-build', '-G', 'Ninja',
        '-DCMAKE_TOOLCHAIN_FILE=' + str(sdk / 'cmake/Switch.cmake'),
        '-DCMAKE_BUILD_TYPE=Release', '-DOOT3D_ENABLE_VULKAN_RENDERER=OFF',
        '-DOOT3D_WHOLE_AOT_PRODUCT_MODE=ON', '-DOOT3D_DIRECT_AOT_PLUGIN=ON',
        '-DOOT3D_REBUILD_WHOLE_AOT=OFF', '-DRETUNED_REPRODUCIBLE_PATHS=ON',
        '-DCMAKE_PROJECT_Oot3dRecomp_INCLUDE=' + str(source / 'LinkTitle.cmake'),
        '-DRETUNED_SWITCH_TITLE_ARCHIVE=' + str(work / 'title-build/libretuned_switch_title.a'),
        *renderer_options)
    run('cmake', '--build', work / 'host-build', '--target', 'oot3d_native_game_nro',
        '--parallel', args.jobs)
    print('Private Switch NRO built. Do not include it in public release assets.')


if __name__ == '__main__':
    main()
