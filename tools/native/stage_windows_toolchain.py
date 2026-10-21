#!/usr/bin/env python3
"""Stage a pinned, self-contained x64 compiler without installed developer tools.

Inputs are original official release archives; no game or developer SDK input is
accepted. The same compiler must build the host and its title modules.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

RELEASES = {
    'llvm': ('mstorsjo/llvm-mingw', '20261006', 'llvm-mingw-20261006-ucrt-x86_64.zip',
             '317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a'),
    'cmake': ('Kitware/CMake', 'v4.4.4', 'cmake-4.4.4-windows-x86_64.zip',
              'bace36e94b31c68ab6fa295f26dfa11219e0701cf7c94b0284a7d1cb13dac536'),
    'ninja': ('ninja-build/ninja', 'v1.13.2', 'ninja-win.zip',
              '07fc8261b42b20e71d1720b39068c2e14ffcee6396b76fb7a795fb460b78dc65'),
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selected(component, path):
    parts = path.parts
    if component == 'ninja':
        return path.as_posix() == 'ninja.exe'
    if component == 'cmake':
        original_notice = (parts[:2] == ('doc', 'cmake') and
                           path.name.lower() in ('license.rst', 'license', 'copying', 'copyright.txt', 'notice'))
        return original_notice or parts[0] in ('share', 'licenses') or path.as_posix() in ('bin/cmake.exe', 'bin/cmcldeps.exe')
    if parts[0] in ('LICENSE.TXT', 'include', 'lib', 'share', 'x86_64-w64-mingw32'):
        return True
    if parts[0] != 'bin':
        return False
    name = parts[-1]
    # libffi belongs to the omitted LLDB/Python stack; no retained tool imports it.
    if name == 'libffi-8.dll':
        return False
    # Keep compiler/linker resource wrappers and DLL dependencies; omit other
    # target architectures, debugger, IDE services and their bundled Python.
    if name.startswith(('aarch64-', 'armv7-', 'arm64ec-', 'i686-', 'lldb', 'liblldb', 'libpython', 'clangd', 'clang-tidy')):
        return False
    return 'uwp' not in name


def stage(archives, ninja_license, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite a toolchain')
    for component, path in archives.items():
        if digest(path) != RELEASES[component][3]:
            raise ValueError('Official archive digest mismatch: ' + component)
    # The original upstream notice is an explicit input, never a synthesized summary.
    if not Path(ninja_license).is_file():
        raise ValueError('Ninja original COPYING is required')
    if digest(ninja_license) != 'eb7e9ab9690124c5c9f42bdc81383d886a3dede26345b6ed15bbad7caf81f7ea':
        raise ValueError('Ninja original COPYING digest mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='windows-tools-') as temporary:
        root = Path(temporary) / 'tools'
        root.mkdir()
        records = []
        for component, archive in archives.items():
            with zipfile.ZipFile(archive) as zipped:
                for entry in zipped.infolist():
                    name = entry.filename
                    path = PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name or stat.S_ISLNK(entry.external_attr >> 16):
                        raise ValueError('Unsafe toolchain archive entry')
                    if entry.is_dir():
                        continue
                    relative = path if component == 'ninja' else PurePosixPath(*path.parts[1:])
                    if not relative.parts or not selected(component, relative):
                        continue
                    destination = root / component / relative
                    if destination.exists():
                        raise ValueError('Duplicate toolchain archive entry')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(entry) as source, destination.open('wb') as target:
                        shutil.copyfileobj(source, target)
            repo, tag, filename, sha = RELEASES[component]
            records.append({'component': component, 'url': f'https://github.com/{repo}/releases/download/{tag}/{filename}',
                            'sha256': sha, 'source': f'https://github.com/{repo}/tree/{tag}'})
        (root / 'licenses').mkdir()
        notice_root = Path(__file__).resolve().parents[2] / 'resources/licenses/windows-tools'
        notice_metadata = json.loads((notice_root / 'sources.json').read_text())
        for record in notice_metadata['licenses']:
            name = record['file']
            if PurePosixPath(name).name != name or digest(notice_root / name) != record['sha256']:
                raise ValueError('Compiler component notice integrity mismatch')
            shutil.copy2(notice_root / name, root / 'licenses' / name)
        shutil.copy2(notice_root / 'sources.json', root / 'licenses/llvm-component-sources.json')
        shutil.copy2(ninja_license, root / 'licenses/ninja-COPYING')
        shutil.copy2(Path(__file__).with_name('windows-toolchain.cmake'), root / 'windows-toolchain.cmake')
        files = {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}
        (root / 'toolchain-manifest.json').write_text(json.dumps({'format': 'retuned_windows_toolchain_v1',
            'abi': 'x86_64-llvm-mingw-ucrt-20261006', 'components': records, 'files': files}, indent=2) + '\n')
        root.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for component in RELEASES:
        parser.add_argument('--' + component, type=Path, required=True)
    parser.add_argument('--ninja-license', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stage({name: getattr(args, name) for name in RELEASES}, args.ninja_license, args.output)
