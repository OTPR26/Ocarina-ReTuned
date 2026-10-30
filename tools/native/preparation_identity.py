"""Content identities for shipped preparation inputs, independent of APK/UI versions."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import zipfile

NATIVE_TOOLS = ('libretuned_clang.so', 'libretuned_lld.so', 'libc++_shared.so')


def stream_hash(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def archive_identity(archive, native_tools):
    files = {}
    seen = set()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            name = entry.filename
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or name in seen:
                raise ValueError('Invalid preparation archive path')
            seen.add(name)
            if name.startswith(("project/tools/frontend/", "project/resources/fonts/interface/")) or (name.startswith("project/") and name.endswith(".java")):
                continue
            with bundle.open(entry) as stream:
                files[name] = stream_hash(stream)
    for name in NATIVE_TOOLS:
        with Path(native_tools[name]).open('rb') as stream:
            files['native/' + name] = stream_hash(stream)
    identity = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return identity


def stamp_android(assets, compiler_directory, runtime_directory):
    from android_runtime import verify_runtime
    assets = Path(assets)
    tools = {name: Path(compiler_directory) / name for name in NATIVE_TOOLS}
    tools['libc++_shared.so'] = Path(runtime_directory) / 'libc++_shared.so'
    libraries = {path.name: path for path in Path(runtime_directory).glob('*.so')}
    verify_runtime(libraries | tools)
    identity = archive_identity(assets / 'preparation-kit.zip', tools)
    path = assets / 'preparation-kit.json'
    metadata = json.loads(path.read_text())
    if metadata.get('format') != 'retuned_preparation_asset_v1':
        raise ValueError('Unsupported preparation asset')
    with (assets / 'preparation-kit.zip').open('rb') as stream:
        metadata['sha256'] = stream_hash(stream)
    with zipfile.ZipFile(assets / 'preparation-kit.zip') as bundle:
        metadata['unpacked_bytes'] = sum(entry.file_size for entry in bundle.infolist())
    metadata['preparation_identity'] = identity
    path.write_text(json.dumps(metadata, sort_keys=True) + '\n')
    return identity


def stamp_desktop(kit):
    kit = Path(kit).resolve()
    base = kit.parent
    metadata = json.loads(kit.read_text())
    if metadata.get('format') != 'retuned_rom_preparation_kit_v1':
        raise ValueError('Unsupported preparation kit')
    files = {}
    def collect(path):
        path = path.resolve()
        if not path.is_relative_to(base):
            raise ValueError('Preparation input escapes kit')
        if path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_file() and '__pycache__' not in child.parts:
                    collect(child)
        else:
            with path.open('rb') as stream:
                files[path.relative_to(base).as_posix()] = stream_hash(stream)
    for name in ('engine', 'ips', 'elf', 'ui_resources', 'hd_font_coverage', 'dialogue_font', 'json_include'):
        if name in metadata:
            collect(base / metadata[name])
    project = (base / metadata['script']).resolve().parents[2]
    collect(project / 'tools/native')
    collect(project / 'tools/reframed')
    for path in (project / 'resources').rglob('*'):
        if path.is_file() and 'interface' not in path.relative_to(project / 'resources').parts:
            collect(path)
    if 'windows_tools' in metadata:
        collect(base / metadata['windows_tools'] / 'toolchain-manifest.json')
    payload = {'files': files, 'cmake_args': metadata.get('cmake_args', [])}
    identity = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata['preparation_identity'] = identity
    kit.write_text(json.dumps(metadata, indent=2) + '\n')
    return identity


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--assets', type=Path)
    target.add_argument('--kit', type=Path)
    parser.add_argument('--compiler-directory', type=Path)
    parser.add_argument('--runtime-directory', type=Path)
    args = parser.parse_args()
    if args.kit:
        stamp_desktop(args.kit)
    elif args.compiler_directory and args.runtime_directory:
        stamp_android(args.assets, args.compiler_directory, args.runtime_directory)
    else:
        parser.error("Android identities require compiler and runtime directories")
