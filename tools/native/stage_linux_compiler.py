#!/usr/bin/env python3
"""Stage a relocatable GCC sysroot from extracted distribution packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


TARGETS = {'x86_64': ('x86_64-linux-gnu', 62), 'aarch64': ('aarch64-linux-gnu', 183)}
COMMON_LICENSES = ('GPL-2', 'GPL-3', 'LGPL-2.1', 'LGPL-3', 'GFDL-1.3')


def stage(sysroot, output, architecture, packages):
    source, output, packages = Path(sysroot).resolve(), Path(output).resolve(), Path(packages)
    triple, machine = TARGETS[architecture]
    receipts = json.loads(packages.read_text())
    if not isinstance(receipts, list) or not receipts or any(
            not all(p.get(k) for k in ('package', 'version', 'source', 'sha256')) for p in receipts):
        raise ValueError('Exact package versions, source names, and archive hashes are required')
    required = [f'usr/bin/{triple}-gcc-13', f'usr/bin/{triple}-g++-13',
                f'usr/bin/{triple}-as', f'usr/bin/{triple}-ld',
                f'usr/libexec/gcc/{triple}/13/cc1plus',
                'usr/include/c++/13/vector', 'usr/include/stdio.h',
                f'usr/lib/{triple}/crt1.o']
    for name in required:
        if not (source / name).is_file():
            raise ValueError('Incomplete compiler sysroot: ' + name)
    for name in required[:5]:
        header = (source / name).read_bytes()[:20]
        if header[:6] != b'\x7fELF\x02\x01' or int.from_bytes(header[18:20], 'little') != machine:
            raise ValueError('Compiler executable architecture mismatch: ' + name)
    for package in receipts:
        name = package['package']
        if '/' in name or not (source / 'usr/share/doc' / name / 'copyright').is_file():
            raise ValueError('Distribution copyright notice missing: ' + name)
    for name in COMMON_LICENSES:
        if not (source / 'usr/share/common-licenses' / name).is_file():
            raise ValueError('Referenced common license text missing: ' + name)
    # Absolute package links would silently use the build machine after relocation.
    for path in source.rglob('*'):
        if path.is_symlink() and (os.path.isabs(os.readlink(path)) or not path.resolve().is_relative_to(source)):
            raise ValueError('Sysroot link escapes package: ' + str(path.relative_to(source)))
        if path.is_symlink() and not path.exists():
            raise ValueError('Sysroot link target is missing: ' + str(path.relative_to(source)))
    if output.exists():
        raise ValueError('Use a fresh compiler output directory')
    output.mkdir(parents=True)
    root = output / 'sysroot'
    shutil.copytree(source, root, symlinks=True)
    # Ubuntu's merged-/usr packages retain /lib references in linker scripts.
    if not (root / 'lib').exists():
        (root / 'lib').symlink_to('usr/lib', target_is_directory=True)
    if (root / 'usr/lib64').is_dir() and not (root / 'lib64').exists():
        (root / 'lib64').symlink_to('usr/lib64', target_is_directory=True)
    runtime = output / 'runtime'
    runtime.mkdir()
    for pattern in ('libisl.so*', 'libmpc.so*', 'libmpfr.so*', 'libgmp.so*',
                    'libz.so*', 'libzstd.so*', 'libstdc++.so*', 'libgcc_s.so*',
                    'libbfd*.so', 'libopcodes*.so', 'libctf*.so*', 'libsframe.so*', 'libjansson.so*'):
        for path in (root / 'usr/lib' / triple).glob(pattern):
            shutil.copy2(path, runtime / path.name, follow_symlinks=True)
    (output / 'bin').mkdir()
    for name in ('as', 'ld', 'ar', 'ranlib', 'strip', 'nm'):
        tool = root / f'usr/bin/{triple}-{name}'
        if tool.is_file():
            (output / 'bin' / name).symlink_to(f'../sysroot/usr/bin/{triple}-{name}')
    for name, compiler in (('cc', 'gcc'), ('c++', 'g++')):
        wrapper = output / 'bin' / name
        wrapper.write_text('#!/bin/sh\nset -eu\n'
            'root=$(CDPATH= cd -- "${0%/*}/.." && pwd)\n'
            'unset LD_PRELOAD GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH\n'
            'export LD_LIBRARY_PATH="$root/runtime"\n'
            f'exec "$root/sysroot/usr/bin/{triple}-{compiler}-13" '
            ' --sysroot="$root/sysroot" '
            '-B"$root/bin/" '
            f'-B"$root/sysroot/usr/libexec/gcc/{triple}/13/" '
            f'-B"$root/sysroot/usr/lib/gcc/{triple}/13/" '
            '-B"$root/sysroot/usr/bin/" '
            + ('-nostdinc++ -isystem "$root/sysroot/usr/include/c++/13" '
               f'-isystem "$root/sysroot/usr/include/{triple}/c++/13" ' if name == 'c++' else '')
            + f'-L"$root/sysroot/usr/lib/{triple}" "$@"\n')
        wrapper.chmod(0o755)
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()}
    links = {p.relative_to(output).as_posix(): os.readlink(p)
             for p in sorted(output.rglob('*')) if p.is_symlink()}
    (output / 'toolchain-manifest.json').write_text(json.dumps({
        'format': 'retuned_linux_toolchain_v1', 'architecture': architecture,
        'packages': receipts, 'files': files, 'links': links}, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sysroot', 'output', 'packages'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--architecture', choices=TARGETS, required=True)
    args = parser.parse_args()
    stage(args.sysroot, args.output, args.architecture, args.packages)
