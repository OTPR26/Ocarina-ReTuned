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
import tempfile
from urllib.parse import quote


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def check_neutral_commands(commands):
    if any(token in commands for token in ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/', '\\oot3d_a32_generated\\')):
        raise ValueError('Refusing translated title compilation')


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
        if not source.is_dir() or not copyright_file.is_file():
            raise ValueError('Missing vcpkg dependency notice or recipe: ' + name)
        if any(path.is_symlink() for path in source.rglob('*')):
            raise ValueError('Unexpected link in dependency recipe: ' + name)
        recipe = json.loads((source / 'vcpkg.json').read_text())
        recipe_version = next((recipe[key] for key in ('version', 'version-string', 'version-semver', 'version-date') if key in recipe), None)
        if recipe_version != version or str(recipe.get('port-version', 0)) != fields.get('Port-Version', '0'):
            raise ValueError('Installed dependency needs a different versioned port recipe: ' + name)
        destination = notices / 'vcpkg' / name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copyright_file, destination / 'copyright')
        shutil.copytree(source, destination / 'port', symlinks=False)
        records.append({'package': name, 'version': version, 'port_version': fields.get('Port-Version', '0'),
            'port_source': 'https://github.com/microsoft/vcpkg/tree/' + revision + '/ports/' + name,
            'copyright': (destination / 'copyright').relative_to(notices).as_posix()})
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
    verify_neutral_shaders(engine, runtime)
    for path in (runtime, stub):
        if not path.is_relative_to(build) or not path.is_file():
            raise ValueError('Runtime target escaped build tree or is missing')
    stem = 'Ocarina-ReTuned-Native-' + ('Windows-x64' if platform == 'windows' else 'Linux-x86_64')
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
        while pending:
            source = pending.pop()
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
                    search.extend(Path(redist).glob('x64/Microsoft.VC*.CRT'))
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
                if path.name.lower() in copied:
                    continue
                copied.add(path.name.lower())
                shutil.copy2(path, root / path.name)
                dependency_sources.append(path)
                pending.append(path)
        resources = root / 'resources'
        resources.mkdir()
        shutil.copy2(engine / 'runtime/triaevum_resources/gamecontrollerdb.txt', resources)
        notices = root / 'licenses'
        notices.mkdir()
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            if (engine / name).is_file():
                shutil.copy2(engine / name, notices / name)
        if (engine / 'LICENSES').is_dir():
            shutil.copytree(engine / 'LICENSES', notices / 'runtime-notices')
        shutil.copy2(Path(__file__).resolve().parents[2] / 'resources/fonts/LICENSE.txt', notices / 'interface-font-OFL.txt')
        if platform == 'linux':
            linux_dependency_notices(dependency_sources, notices)
        else:
            windows_dependency_notices(engine.parent / 'dependencies/vcpkg', notices, windows_triplet)
        (root / 'README.txt').write_text('Ocarina ReTuned desktop host preview\n\nThis neutral host contains no ROM, title library or game assets.\nA locally prepared, platform-matching title is required for gameplay.\nUse --launch-profile with your local launch profile for testing.\n')
        if platform == 'linux':
            launcher = root / 'Ocarina-ReTuned.sh'
            launcher.write_text('#!/bin/sh\nset -eu\nroot=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport LD_LIBRARY_PATH="$root${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$root/OcarinaReTuned" "$@"\n')
            launcher.chmod(0o755)
            env = dict(os.environ, LD_LIBRARY_PATH=str(root))
        else:
            env = dict(os.environ)
        result = subprocess.run([str(executable), '--product-info'], cwd=root, env=env, check=True, text=True, capture_output=True)
        (root / 'product-info.json').write_text(result.stdout)
        files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        (root / 'package-manifest.json').write_text(json.dumps({'schema':1, 'platform':platform, 'files':files}, indent=2)+'\n')
        shutil.make_archive(str(output / stem), 'zip' if platform == 'windows' else 'gztar', temp, stem)
    print(archive.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('windows', 'linux'), required=True)
    parser.add_argument('--windows-triplet', choices=('x64-windows-static', 'x64-mingw-static'), default='x64-windows-static')
    for name in ('engine', 'build', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.platform, args.engine, args.build, args.output, args.windows_triplet)
