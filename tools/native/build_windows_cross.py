#!/usr/bin/env python3
"""Build the neutral Windows host using the official LLVM-MinGW macOS tools.

Supply LLVM-MinGW 20261006 and vcpkg ef7dbf94b9198bc58f45951adcf1f041fcbc5ea0.
No ROM or generated title module is needed. Build outputs stay in --work.
"""
import argparse
import os
from pathlib import Path
import subprocess

VCPKG_REVISION = 'ef7dbf94b9198bc58f45951adcf1f041fcbc5ea0'
PACKAGES = ['zlib', 'bzip2', 'libzip', 'libpng', 'sdl2', 'glew', 'glfw3',
            'nlohmann-json', 'tinyxml2', 'spdlog', 'libogg', 'libvorbis',
            'opus', 'opusfile', 'shaderc', 'vulkan-headers', 'vulkan-loader']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'llvm', 'vcpkg', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--arch', choices=('x64', 'arm64'), required=True)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    project = Path(__file__).resolve().parents[2]
    engine, llvm, vcpkg, work = (p.resolve() for p in
                                (args.engine, args.llvm, args.vcpkg, args.work))
    revision = subprocess.check_output(['git', '-C', str(vcpkg), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != VCPKG_REVISION:
        raise ValueError('Unexpected vcpkg revision')
    compiler = subprocess.check_output([str(llvm / 'bin/clang'), '--version'], text=True)
    if '23.1.3' not in compiler:
        raise ValueError('LLVM-MinGW Clang 23.1.3 is required')
    work.mkdir(parents=True, exist_ok=True)
    triple, processor = ('aarch64', 'ARM64') if args.arch == 'arm64' else ('x86_64', 'x86_64')
    triplet = args.arch + '-mingw-static'
    chain = work / 'windows-chain.cmake'
    chain.write_text(f'''set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR {processor})
set(CMAKE_VS_PLATFORM_NAME {'ARM64' if args.arch == 'arm64' else 'x64'})
set(CMAKE_C_COMPILER "{llvm}/bin/{triple}-w64-mingw32-clang")
set(CMAKE_CXX_COMPILER "{llvm}/bin/{triple}-w64-mingw32-clang++")
set(CMAKE_RC_COMPILER "{llvm}/bin/{triple}-w64-mingw32-windres")
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-static")
add_compile_options("-D_WIN32_WINNT=0x0A00" "-DWINVER=0x0A00")
add_compile_options("-ffile-prefix-map={Path.home()}=builder")
''')
    triplets = work / 'triplets'
    triplets.mkdir(exist_ok=True)
    (triplets / (triplet + '.cmake')).write_text(f'''set(VCPKG_TARGET_ARCHITECTURE {args.arch})
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)
set(VCPKG_CMAKE_SYSTEM_NAME MinGW)
set(VCPKG_CHAINLOAD_TOOLCHAIN_FILE "{chain}")
''')
    environment = dict(os.environ, VCPKG_DISABLE_METRICS='1',
                       VCPKG_MAX_CONCURRENCY=str(args.jobs),
                       VCPKG_OVERLAY_TRIPLETS=str(triplets),
                       VCPKG_OVERLAY_PORTS=str(Path(__file__).with_name('windows-cross-ports')),
                       VCPKG_ROOT=str(vcpkg))
    environment['PATH'] = str(llvm / 'bin') + os.pathsep + environment.get('PATH', '')

    def run(*arguments):
        subprocess.run(list(map(str, arguments)), env=environment, check=True)

    for script in ('tools/native/apply_desktop_port.py', 'tools/reframed/apply_native_port.py',
                   'tools/reframed/apply_renderer_port.py', 'tools/native/apply_audio_port.py',
                   'tools/frontend/apply_frontend_port.py'):
        extra = ['--portable-windows'] if script.endswith('apply_desktop_port.py') else []
        run('python3', project / script, engine, *extra)
    run(vcpkg / 'vcpkg', 'install', '--triplet=' + triplet,
        '--host-triplet=arm64-osx', '--disable-metrics', *PACKAGES)
    run('python3', project / 'tools/native/fix_windows_fmt.py', vcpkg / 'installed' / triplet / 'include')
    preload = work / 'static-shaderc.cmake'
    preload.write_text(f'''if(NOT TARGET three_ds_recomp_shaderc)
find_package(unofficial-shaderc CONFIG REQUIRED)
add_library(three_ds_recomp_shaderc STATIC IMPORTED GLOBAL)
set_target_properties(three_ds_recomp_shaderc PROPERTIES
 IMPORTED_LOCATION "{vcpkg}/installed/{triplet}/lib/libshaderc.a"
 INTERFACE_LINK_LIBRARIES unofficial::shaderc::shaderc
 INTERFACE_COMPILE_DEFINITIONS RETUNED_STATIC_SHADERC)
endif()
''')
    flags = {'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_TOOLCHAIN_FILE': str(vcpkg / 'scripts/buildsystems/vcpkg.cmake'),
             'VCPKG_CHAINLOAD_TOOLCHAIN_FILE': str(chain), 'VCPKG_APPLOCAL_DEPS': 'OFF',
             'VCPKG_TARGET_TRIPLET': triplet, 'VCPKG_TRIPLET': triplet,
             'VCPKG_HOST_TRIPLET': 'arm64-osx', 'AUTOMATE_VCPKG_UPDATE': 'OFF',
             'CMAKE_PROJECT_INCLUDE': str(preload), 'OOT3D_WHOLE_AOT_PRODUCT_MODE': 'ON',
             'OOT3D_DIRECT_AOT_PLUGIN': 'ON', 'OOT3D_ENABLE_VULKAN_RENDERER': 'ON',
             'THREE_DS_RECOMP_ENABLE_NRI': 'ON'}
    for option in ('IMMERSE', 'NRI_UPSCALER_SDKS', 'DLSS_MODULE', 'SSSR', 'CACAO'):
        flags['THREE_DS_RECOMP_ENABLE_' + option] = 'OFF'
    flags.update(THREE_DS_RECOMP_OFFER_EXPERIMENTAL_GI='OFF', ENABLE_SCRIPTING='OFF', INCLUDE_MPQ_SUPPORT='OFF')
    run('cmake', '-S', engine, '-B', work / 'build', '-G', 'Ninja',
        *['-D' + key + '=' + value for key, value in flags.items()])
    run('cmake', '--build', work / 'build', '--target', 'triaevum_public_runtime',
        '--parallel', args.jobs)


if __name__ == '__main__':
    main()
