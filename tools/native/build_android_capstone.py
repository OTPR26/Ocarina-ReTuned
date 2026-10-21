#!/usr/bin/env python3
"""Build the pinned ARM decoder without embedding developer directory names."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile

SOURCE_SHA256 = 'b11a87d67751b006b9b44428d59c99512e6d6c89cf7dff8cdd92d9065628b5a0'


def build(archive, ndk, output):
    archive, ndk, output = (Path(p).resolve() for p in (archive, ndk, output))
    if sys.platform not in ('darwin', 'linux'):
        raise ValueError('This cross-build recipe supports macOS and Linux hosts.')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Expected the original Capstone 5.0.6 source archive.')
    if output.exists():
        raise ValueError('Choose a new build directory; existing output is preserved.')
    toolchain = ndk / 'build/cmake/android.toolchain.cmake'
    if not toolchain.is_file():
        raise ValueError('A complete Android NDK is required.')
    output.mkdir(parents=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe source archive entry.')
        source.extractall(output / 'source', filter='data')
    source = output / 'source/capstone-5.0.6/src'
    binary = output / 'build'
    flags = ' '.join(shlex.quote('-ffile-prefix-map=' + str(path) + '=' + neutral)
        for path, neutral in ((source, '/src/capstone'), (output, '/build/capstone'), (ndk, '/opt/android-ndk')))
    subprocess.run(['cmake', '-S', str(source), '-B', str(binary), '-G', 'Ninja',
        '-DCMAKE_TOOLCHAIN_FILE=' + str(toolchain), '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-29',
        '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_C_FLAGS=' + flags, '-DCMAKE_C_FLAGS_RELEASE=',
        '-DBUILD_SHARED_LIBS=ON', '-DBUILD_STATIC_LIBS=OFF', '-DCAPSTONE_ARCHITECTURE_DEFAULT=OFF',
        '-DCAPSTONE_ARM_SUPPORT=ON', '-DCAPSTONE_BUILD_TESTS=OFF', '-DCAPSTONE_BUILD_CSTOOL=OFF',
        '-DCAPSTONE_BUILD_CSTEST=OFF', '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384'], check=True)
    subprocess.run(['cmake', '--build', str(binary), '--parallel', '3'], check=True)
    library = binary / 'libcapstone.so'
    data = library.read_bytes()
    if any(token in data for token in (str(output).encode(), str(source).encode(), str(ndk).encode(), b'work/private')):
        raise ValueError('A developer build path survived prefix mapping.')
    receipt = {'source_version': '5.0.6', 'source_sha256': SOURCE_SHA256,
        'ndk': (ndk / 'source.properties').read_text(), 'architecture': 'arm64-v8a', 'api': 29,
        'library_sha256': hashlib.sha256(data).hexdigest(), 'private_path_scan': 'pass'}
    (output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return library


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'ndk', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(build(args.archive, args.ndk, args.output))
