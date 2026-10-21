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


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def check_neutral_commands(commands):
    if any(token in commands for token in ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/', '\\oot3d_a32_generated\\')):
        raise ValueError('Refusing translated title compilation')


def stage(platform, engine, build, output):
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
        while pending:
            source = pending.pop()
            if platform == 'linux':
                listing = run('ldd', str(source))
                if 'not found' in listing:
                    raise ValueError('Unresolved runtime library: ' + listing)
                libraries = [Path(p) for p in re.findall(r'=> (/\S+)', listing)]
                # Keep glibc, display/driver libraries and the Vulkan loader supplied by the OS.
                system = ('libc.so', 'libm.so', 'libdl.so', 'libpthread.so', 'librt.so', 'libresolv.so',
                          'libvulkan.so', 'libGL', 'libEGL', 'libX', 'libxcb', 'libwayland', 'libdrm',
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
                pending.append(path)
        resources = root / 'resources'
        resources.mkdir()
        shutil.copy2(engine / 'runtime/triaevum_resources/gamecontrollerdb.txt', resources)
        notices = root / 'licenses'
        notices.mkdir()
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            if (engine / name).is_file():
                shutil.copy2(engine / name, notices / name)
        shutil.copy2(Path(__file__).resolve().parents[2] / 'resources/fonts/LICENSE.txt', notices / 'interface-font-OFL.txt')
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
    for name in ('engine', 'build', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.platform, args.engine, args.build, args.output)
