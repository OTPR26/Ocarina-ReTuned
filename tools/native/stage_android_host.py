#!/usr/bin/env python3
"""Archive only neutral Android host libraries, excluding translated title code."""
import argparse
from audit_neutral_shaders import verify as verify_neutral_shaders
from android_runtime import verify_runtime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

SYSTEM_LIBRARIES = {'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libandroid.so',
    'libEGL.so', 'libGLESv1_CM.so', 'libGLESv2.so', 'libGLESv3.so', 'libvulkan.so',
    'libOpenSLES.so', 'libaaudio.so', 'libz.so'}


def stage(engine, build, ndk, output):
    engine, build, ndk, output = map(lambda p: Path(p).resolve(), (engine, build, ndk, output))
    if output.exists():
        raise ValueError('Refusing to replace an existing host archive.')
    cache = (build / 'CMakeCache.txt').read_text()
    configured = re.search(r'^CMAKE_TOOLCHAIN_FILE:[^=]+=(.+)$', cache, re.MULTILINE)
    if not configured or Path(configured[1]).resolve() != ndk / 'build/cmake/android.toolchain.cmake':
        raise ValueError('Staging NDK must match the native build toolchain.')
    llvm = ndk / 'toolchains/llvm/prebuilt' / ('darwin-x86_64' if sys.platform == 'darwin' else 'linux-x86_64')
    sources = {
        'libSDL2.so': build / '_deps/sdl2-build/libSDL2.so',
        'libTriAevum.so': build / 'product/libTriAevum.so',
        'libtriaevum_title_bootstrap.so': build / 'product/libtriaevum_title_bootstrap.so',
        'libc++_shared.so': llvm / 'sysroot/usr/lib/aarch64-linux-android/libc++_shared.so',
    }
    commands = subprocess.check_output(['ninja', '-C', str(build), '-t', 'commands', 'oot3d_native_game'], text=True)
    verify_runtime(sources)
    if any(token in commands for token in ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/')):
        raise ValueError('The public host must not compile game-derived title sources.')
    verify_neutral_shaders(engine, sources['libTriAevum.so'])
    allowed = SYSTEM_LIBRARIES | set(sources)
    with tempfile.TemporaryDirectory(prefix='retuned-host-') as temporary:
        root = Path(temporary) / 'Ocarina-ReTuned-Native-Android'
        libraries = root / 'arm64-v8a'
        libraries.mkdir(parents=True)
        records = {}
        for name, source in sources.items():
            header = subprocess.check_output([str(llvm / 'bin/llvm-readelf'), '-h', str(source)], text=True)
            if 'AArch64' not in header:
                raise ValueError('Host library is not AArch64: ' + name)
            dynamic = subprocess.check_output([str(llvm / 'bin/llvm-readelf'), '-d', str(source)], text=True)
            needed = set(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic))
            if needed - allowed:
                raise ValueError('Unpackaged host dependency: ' + name)
            segments = subprocess.check_output([str(llvm / 'bin/llvm-readelf'), '-l', '--wide', str(source)], text=True)
            loads = [line for line in segments.splitlines() if line.strip().startswith('LOAD ')]
            if not loads or any(int(line.split()[-1], 16) < 16384 for line in loads):
                raise ValueError('Host library lacks 16-KiB load alignment: ' + name)
            destination = libraries / name
            shutil.copy2(source, destination)
            subprocess.run([str(llvm / 'bin/llvm-strip'), '--strip-debug', str(destination)], check=True)
            records[name] = {'bytes': destination.stat().st_size,
                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'needed': sorted(needed)}
        (root / 'native-host.json').write_text(json.dumps({'schema': 1,
            'runtime_revision': '17218b0cfdb944645bb5cde5249f313dca7e53ce',
            'target': 'aarch64-linux-android', 'title_included': False, 'libraries': records}, indent=2) + '\n')
        notices = root / 'licenses'
        notices.mkdir()
        for name in ('LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            shutil.copy2(engine / name, notices / name)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(output, 'x:gz') as archive:
            archive.add(root, arcname=root.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'build', 'ndk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.engine, args.build, args.ndk, args.output)
