#!/usr/bin/env python3
"""Stage only the neutral desktop host and its runtime dependency closure."""
import argparse
from audit_neutral_shaders import verify as verify_neutral_shaders
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sysconfig
import tempfile
from urllib.parse import quote
from runtime_notices import copy_runtime_donor_notices
from runtime_paths import verify_runtime_paths


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def check_neutral_commands(commands):
    if any(token in commands for token in ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/', '\\oot3d_a32_generated\\')):
        raise ValueError('Refusing translated title compilation')


def binary_architecture(path, platform):
    """Read the binary header instead of trusting build-folder or host names."""
    with Path(path).open('rb') as stream:
        header = stream.read(64)
        if platform == 'linux' and header[:6] == b'\x7fELF\x02\x01':
            machine = int.from_bytes(header[18:20], 'little')
            architectures = {62: 'x86_64', 183: 'arm64'}
        elif platform == 'windows' and header[:2] == b'MZ' and len(header) == 64:
            stream.seek(int.from_bytes(header[60:64], 'little'))
            signature = stream.read(6)
            if signature[:4] != b'PE\0\0':
                raise ValueError('Invalid Windows binary header')
            machine = int.from_bytes(signature[4:6], 'little')
            architectures = {0x8664: 'x86_64', 0xAA64: 'arm64'}
        else:
            raise ValueError('Unsupported desktop binary format')
    if machine not in architectures:
        raise ValueError('Unsupported desktop binary architecture')
    return architectures[machine]


def linux_audio_runtime(root, lib_root, config_root=Path('/usr/share/pipewire')):
    """SDL loads PipeWire and its plugins at runtime, outside ldd's closure."""
    lib_root = Path(lib_root)
    required = [lib_root / 'libpipewire-0.3.so.0', config_root / 'client.conf',
                lib_root / 'pipewire-0.3/libpipewire-module-protocol-native.so',
                lib_root / 'spa-0.2/support/libspa-support.so',
                lib_root / 'spa-0.2/audioconvert/libspa-audioconvert.so']
    for path in required:
        if not path.is_file():
            raise ValueError('Missing PipeWire client runtime: ' + str(path))
    files = [(required[0], root / required[0].name)]
    for directory in ('pipewire-0.3', 'spa-0.2'):
        for path in sorted((lib_root / directory).rglob('*.so')):
            files.append((path, root / directory / path.relative_to(lib_root / directory)))
    for path in sorted(config_root.rglob('*.conf')):
        files.append((path, root / 'share/pipewire' / path.relative_to(config_root)))
    for source, destination in files:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return [source for source, _ in files]


def linux_launcher():
    return '''#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PATH="$root/setup/build-tools/cmake/bin:$root/setup/build-tools/ninja:$PATH"
export LD_LIBRARY_PATH="$root${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PIPEWIRE_CONFIG_DIR="${PIPEWIRE_CONFIG_DIR:-$root/share/pipewire}"
export PIPEWIRE_MODULE_DIR="${PIPEWIRE_MODULE_DIR:-$root/pipewire-0.3}"
export SPA_PLUGIN_DIR="${SPA_PLUGIN_DIR:-$root/spa-0.2}"
# Prefer the native client when a user-session PipeWire server is available.
# Keep explicit user driver choices, including remote-session configurations.
if [ -z "${SDL_AUDIODRIVER:-}" ] && [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -S "$XDG_RUNTIME_DIR/pipewire-0" ]; then
    export SDL_AUDIODRIVER=pipewire
fi
exec "$root/OcarinaReTuned" "$@"
'''


def linux_dependency_notices(libraries, notices, doc_root=Path('/usr/share/doc'), common_root=Path('/usr/share/common-licenses')):
    """Keep the distro's complete notices and exact source version for each DSO."""
    records = []
    for library in sorted(libraries, key=lambda p: p.name):
        owners = set()
        # dpkg may record the pre-usrmerge spelling even when ldd uses /usr/lib.
        candidates = {str(library), str(library.resolve())}
        candidates.update(p.removeprefix('/usr') for p in tuple(candidates) if p.startswith('/usr/lib/'))
        for candidate in sorted(candidates):
            result = subprocess.run(['dpkg-query', '-S', candidate], text=True, capture_output=True)
            if result.returncode == 0:
                owners.update(line.rsplit(': ', 1)[0] for line in result.stdout.splitlines() if ': ' in line)
        if len(owners) != 1:
            raise ValueError('Cannot identify dependency package: ' + library.name)
        package = owners.pop()
        fields = run('dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}', package).strip().split('\t')
        if len(fields) != 4 or not all(fields):
            raise ValueError('Incomplete dependency source metadata: ' + package)
        binary_package, version, source_package, source_version = fields
        name = binary_package.split(':')[0]
        copyright_file = doc_root / name / 'copyright'
        if not copyright_file.is_file():
            raise ValueError('Missing dependency copyright notice: ' + package)
        destination = notices / 'dependencies' / name / 'copyright'
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copyright_file, destination)
        for common in set(re.findall(r'/usr/share/common-licenses/([A-Za-z0-9.+-]+)', copyright_file.read_text())):
            common = common.rstrip('.')
            common_source = common_root / common
            if not common_source.is_file():
                raise ValueError('Missing common license text: ' + common)
            common_destination = notices / 'common-licenses' / common
            common_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(common_source, common_destination)
        records.append({'library': library.name, 'binary_package': binary_package, 'version': version,
            'source_package': source_package, 'source_version': source_version,
            'source_record': 'https://launchpad.net/ubuntu/+source/' + quote(source_package, safe='') + '/' + quote(source_version, safe=''),
            'copyright': destination.relative_to(notices).as_posix()})
    (notices / 'linux-dependency-sources.json').write_text(json.dumps({'schema': 1, 'dependencies': records}, indent=2) + '\n')


def windows_dependency_notices(vcpkg, notices, triplet='x64-windows-static'):
    """Static libraries still require notices and their versioned port recipes."""
    revision = run('git', '-C', str(vcpkg), 'rev-parse', 'HEAD').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Cannot identify vcpkg source revision')
    installed = vcpkg / 'installed'
    paragraphs = (installed / 'vcpkg/status').read_text().split('\n\n')
    records = []
    for paragraph in paragraphs:
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Architecture') != triplet or 'Feature' in fields:
            continue
        name, version = fields.get('Package', ''), fields.get('Version', '')
        if not re.fullmatch(r'[a-z0-9-]+', name) or not version:
            raise ValueError('Incomplete vcpkg dependency identity')
        source = vcpkg / 'ports' / name
        copyright_file = installed / triplet / 'share' / name / 'copyright'
        if not source.is_dir():
            raise ValueError('Missing vcpkg dependency notice or recipe: ' + name)
        if any(path.is_symlink() for path in source.rglob('*')):
            raise ValueError('Unexpected link in dependency recipe: ' + name)
        recipe = json.loads((source / 'vcpkg.json').read_text())
        system_opengl = (name == 'opengl' and recipe.get('license', 'unspecified') is None
            and 'VCPKG_POLICY_EMPTY_PACKAGE' in (source / 'portfile.cmake').read_text())
        if not copyright_file.is_file() and not system_opengl:
            raise ValueError('Missing vcpkg dependency notice: ' + name)
        recipe_version = next((recipe[key] for key in ('version', 'version-string', 'version-semver', 'version-date') if key in recipe), None)
        if recipe_version != version or str(recipe.get('port-version', 0)) != fields.get('Port-Version', '0'):
            raise ValueError('Installed dependency needs a different versioned port recipe: ' + name)
        destination = notices / 'vcpkg' / name
        destination.mkdir(parents=True, exist_ok=True)
        if copyright_file.is_file():
            shutil.copy2(copyright_file, destination / 'copyright')
        shutil.copytree(source, destination / 'port', symlinks=False)
        records.append({'package': name, 'version': version, 'port_version': fields.get('Port-Version', '0'),
            'port_source': 'https://github.com/microsoft/vcpkg/tree/' + revision + '/ports/' + name,
            'copyright': (destination / 'copyright').relative_to(notices).as_posix() if copyright_file.is_file() else None,
            'system_component': 'Windows OpenGL runtime supplied by the operating system; registry notices are recorded separately' if system_opengl else None})
    if not records:
        raise ValueError('No Windows static dependency notices were collected')
    (notices / 'windows-dependency-sources.json').write_text(json.dumps({'schema': 1,
        'vcpkg_revision': revision, 'dependencies': records,
        'project_modifications': ['tools/native/fix_windows_fmt.py (format-checker compatibility patch; project source)']}, indent=2) + '\n')


def stage(platform, engine, build, output, windows_triplet='x64-windows-static'):
    engine, build, output = map(lambda p: Path(p).resolve(), (engine, build, output))
    check_neutral_commands(run('ninja', '-C', str(build), '-t', 'commands', 'triaevum_public_runtime'))
    targets = json.loads((build / 'triaevum-runtime-targets-Release.json').read_text())
    runtime, stub = (Path(targets[key]).resolve() for key in ('runtime', 'stub'))
    architecture = binary_architecture(runtime, platform)
    if binary_architecture(stub, platform) != architecture:
        raise ValueError('Host and module architecture mismatch')
    if platform == 'windows' and windows_triplet.split('-')[0] != ('arm64' if architecture == 'arm64' else 'x64'):
        raise ValueError('Windows dependency triplet architecture mismatch')
    verify_neutral_shaders(engine, runtime)
    for path in (runtime, stub):
        if not path.is_relative_to(build) or not path.is_file():
            raise ValueError('Runtime target escaped build tree or is missing')
    suffix = 'ARM64' if architecture == 'arm64' else ('x64' if platform == 'windows' else 'x86_64')
    stem = 'Ocarina-ReTuned-Native-' + platform.title() + '-' + suffix
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (stem + ('.zip' if platform == 'windows' else '.tar.gz'))
    if archive.exists():
        raise ValueError('Refusing archive overwrite')
    with tempfile.TemporaryDirectory(prefix='retuned-desktop-') as temp:
        root = Path(temp) / stem
        root.mkdir()
        executable = root / ('OcarinaReTuned.exe' if platform == 'windows' else 'OcarinaReTuned')
        shutil.copy2(runtime, executable)
        shutil.copy2(stub, root / stub.name)
        pending = [runtime, stub]
        copied = {runtime.name.lower(), stub.name.lower()}
        dependency_sources = []
        if platform == 'linux':
            multiarch = sysconfig.get_config_var('MULTIARCH')
            if not multiarch or not re.fullmatch(r'[A-Za-z0-9_-]+', multiarch):
                raise ValueError('Cannot identify Linux library architecture')
            audio_sources = linux_audio_runtime(root, Path('/usr/lib') / multiarch)
            dependency_sources.extend(audio_sources)
            pending.extend(p for p in audio_sources if '.so' in p.name)
            copied.update(p.name.lower() for p in audio_sources if '.so' in p.name)
        while pending:
            source = pending.pop()
            if binary_architecture(source, platform) != architecture:
                raise ValueError('Runtime dependency architecture mismatch: ' + source.name)
            if platform == 'linux':
                listing = run('ldd', str(source))
                if 'not found' in listing:
                    raise ValueError('Unresolved runtime library: ' + listing)
                libraries = [Path(p) for p in re.findall(r'=> (/\S+)', listing)]
                # Keep glibc, display/driver libraries and the Vulkan loader supplied by the OS.
                system = ('libc.so', 'libm.so', 'libdl.so', 'libpthread.so', 'librt.so', 'libresolv.so',
                          'libvulkan.so', 'libGL.so', 'libGLX.so', 'libGLdispatch.so', 'libEGL', 'libX', 'libxcb', 'libwayland', 'libdrm',
                          'libgbm', 'libudev', 'libasound', 'libpulse', 'libdecor')
                libraries = [p for p in libraries if not p.name.startswith(system)]
            else:
                listing = run('dumpbin', '/nologo', '/dependents', str(source))
                names = re.findall(r'^\s+([\w.+-]+\.dll)\s*$', listing, re.M | re.I)
                search = [build, Path(os.environ['VULKAN_SDK']) / 'Bin']
                redist = os.environ.get('VCToolsRedistDir')
                if redist:
                    search.extend(Path(redist).glob(('arm64' if architecture == 'arm64' else 'x64') + '/Microsoft.VC*.CRT'))
                search.extend(Path(p) for p in os.environ.get('PATH', '').split(os.pathsep) if p)
                libraries = []
                for name in names:
                    if name.lower().startswith(('api-ms-', 'ext-ms-')):
                        continue
                    match = next((p / name for p in search if (p / name).is_file()), None)
                    if match is None:
                        raise ValueError('Unresolved Windows runtime library: ' + name)
                    if str(match).lower().startswith(str(Path(os.environ['SystemRoot'])).lower()):
                        if name.lower().startswith(('msvcp', 'vcruntime', 'concrt')):
                            raise ValueError('Visual C++ runtime must be bundled from its redistributable: ' + name)
                        continue
                    libraries.append(match)
            for path in libraries:
                if binary_architecture(path, platform) != architecture:
                    raise ValueError('Runtime dependency architecture mismatch: ' + path.name)
                if path.name.lower() in copied:
                    continue
                copied.add(path.name.lower())
                shutil.copy2(path, root / path.name)
                dependency_sources.append(path)
                pending.append(path)
        resources = root / 'resources'
        verify_runtime_paths([p for p in root.iterdir() if p.is_file()],
                             [engine, build, Path(__file__).resolve().parents[2], Path.home()])
        resources.mkdir()
        shutil.copy2(engine / 'runtime/triaevum_resources/gamecontrollerdb.txt', resources)
        notices = root / 'licenses'
        notices.mkdir()
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            if (engine / name).is_file():
                shutil.copy2(engine / name, notices / name)
        if (engine / 'LICENSES').is_dir():
            shutil.copytree(engine / 'LICENSES', notices / 'runtime-notices')
        copy_runtime_donor_notices(engine, notices)
        shutil.copy2(Path(__file__).resolve().parents[2] / 'resources/fonts/LICENSE.txt', notices / 'interface-font-OFL.txt')
        shutil.copytree(Path(__file__).resolve().parents[2]/'resources/fonts/interface',notices/'interface-fonts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.ttf'))
        if platform == 'linux':
            linux_dependency_notices(dependency_sources, notices)
        else:
            windows_dependency_notices(engine.parent / 'dependencies/vcpkg', notices, windows_triplet)
            if windows_triplet in ('x64-mingw-static', 'arm64-mingw-static'):
                (root / 'preparation-abi.json').write_text(json.dumps({
                    'abi': ('aarch64' if architecture == 'arm64' else 'x86_64') + '-llvm-mingw-ucrt-20261006',
                    'host_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}, indent=2) + '\n')
        (root / 'README.txt').write_text('Ocarina ReTuned desktop host preview\n\nThis neutral host contains no ROM, title library or game assets.\nA locally prepared, platform-matching title is required for gameplay.\nUse --launch-profile with your local launch profile for testing.\n')
        if platform == 'linux':
            launcher = root / 'Ocarina-ReTuned.sh'
            launcher.write_text(linux_launcher())
            launcher.chmod(0o755)
            (root / 'OcarinaReTuned.desktop').write_text('[Desktop Entry]\nType=Application\nName=Ocarina ReTuned\nComment=Ocarina ReTuned Preview\nExec=Ocarina-ReTuned.sh\nIcon=OcarinaReTuned\nCategories=Game;\nTerminal=false\nStartupWMClass=io.github.otpr26.ocarinaretuned\n')
            shutil.copy2(Path(__file__).resolve().parents[2] / 'resources/icons/android/mipmap-xxxhdpi/ic_launcher.png', root / 'OcarinaReTuned.png')
            env = dict(os.environ, LD_LIBRARY_PATH=str(root))
        else:
            env = dict(os.environ)
        result = subprocess.run([str(executable), '--product-info'], cwd=root, env=env, check=True, text=True, capture_output=True)
        (root / 'product-info.json').write_text(result.stdout)
        files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        (root / 'package-manifest.json').write_text(json.dumps({'schema':1, 'platform':platform,
            'architecture':architecture, 'files':files}, indent=2)+'\n')
        shutil.make_archive(str(output / stem), 'zip' if platform == 'windows' else 'gztar', temp, stem)
    print(archive.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('windows', 'linux'), required=True)
    parser.add_argument('--windows-triplet', choices=('x64-windows-static', 'x64-mingw-static',
        'arm64-windows-static', 'arm64-mingw-static'), default='x64-windows-static')
    for name in ('engine', 'build', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.platform, args.engine, args.build, args.output, args.windows_triplet)
