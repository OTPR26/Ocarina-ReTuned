#!/usr/bin/env python3
"""Bundle a neutral ARM64 runtime; title code and game data stay on the user's Mac."""
import argparse
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def package(engine, build, output):
    engine, build, output = Path(engine).resolve(), Path(build).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite an existing package.')
    commands = run('ninja', '-C', str(build), '-t', 'commands', 'triaevum_public_runtime')
    forbidden = ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/')
    if any(token in commands for token in forbidden):
        raise ValueError('A neutral build must not compile translated game files.')
    source = build / 'TriAevum'
    if run('lipo', '-archs', str(source)) != 'arm64':
        raise ValueError('Expected an Apple Silicon runtime.')
    with tempfile.TemporaryDirectory(prefix='retuned-package-') as temporary:
        app = Path(temporary) / 'Ocarina ReTuned.app'
        contents = app / 'Contents'
        macos = contents / 'MacOS'
        resources = contents / 'Resources'
        frameworks = contents / 'Frameworks'
        for directory in (macos, resources, frameworks):
            directory.mkdir(parents=True, exist_ok=True)
        binary = macos / 'retuned-native'
        shutil.copy2(source, binary)
        subprocess.run(['dylibbundler', '-od', '-b', '-x', str(binary), '-d', str(frameworks),
                        '-p', '@executable_path/../Frameworks/', '-s', str(build)],
                        check=True, input='quit\n', text=True, timeout=120)
        # Homebrew SDL2 may be sdl2-compat, which loads SDL3 at runtime.
        if b'libSDL3.dylib' in (frameworks / 'libSDL2-2.0.0.dylib').read_bytes():
            sdl3 = Path(run('brew', '--prefix', 'sdl3')) / 'lib/libSDL3.dylib'
            shutil.copy2(sdl3.resolve(), frameworks / 'libSDL3.dylib')
            subprocess.run(['dylibbundler', '-od', '-b', '-x', str(frameworks / 'libSDL3.dylib'),
                            '-d', str(frameworks), '-p', '@loader_path/', '-s', str(sdl3.parent)],
                            check=True, input='quit\n', text=True, timeout=120)
        molten = Path(run('brew', '--prefix', 'molten-vk'))
        libraries = sorted(molten.rglob('libMoltenVK.dylib'))
        if not libraries:
            raise ValueError('Missing MoltenVK runtime.')
        shutil.copy2(libraries[0], frameworks / 'libMoltenVK.dylib')
        subprocess.run(['install_name_tool', '-id', '@rpath/libMoltenVK.dylib',
                        str(frameworks / 'libMoltenVK.dylib')], check=True)
        icd = resources / 'vulkan/icd.d'
        icd.mkdir(parents=True)
        manifests = sorted(molten.rglob('MoltenVK_icd.json'))
        if not manifests:
            raise ValueError('Missing MoltenVK driver manifest.')
        driver = json.loads(manifests[0].read_text())
        driver['ICD']['library_path'] = '../../../Frameworks/libMoltenVK.dylib'
        (icd / 'MoltenVK_icd.json').write_text(json.dumps(driver, indent=2) + '\n')
        launcher = macos / 'OcarinaReTuned'
        launcher.write_text('''#!/bin/sh
set -eu
contents=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
data_root="$HOME/Library/Application Support/Ocarina ReTuned"
mkdir -p "$data_root"
cd "$data_root"
export VK_ICD_FILENAMES="$contents/Resources/vulkan/icd.d/MoltenVK_icd.json"
export DYLD_LIBRARY_PATH="$contents/Frameworks"
exec "$contents/MacOS/retuned-native" --launch-profile "$HOME/Library/Application Support/Ocarina ReTuned/native-launch.json" "$@"
''')
        launcher.chmod(0o755)
        metadata = {'CFBundleName': 'Ocarina ReTuned', 'CFBundleDisplayName': 'Ocarina ReTuned',
            'CFBundleExecutable': 'OcarinaReTuned', 'CFBundleIdentifier': 'io.github.otpr26.ocarinaretuned',
            'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
            'CFBundleShortVersionString': '0.1.0', 'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '13.4'}
        (contents / 'Info.plist').write_bytes(plistlib.dumps(metadata))
        notices = resources / 'licenses'
        notices.mkdir()
        for name in ('LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            shutil.copy2(engine / name, notices / name)
        for license_name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt'):
            if (engine / license_name).is_file():
                shutil.copy2(engine / license_name, notices / license_name)
        for path in (binary, *frameworks.iterdir()):
            if path.is_file():
                subprocess.run(['codesign', '--force', '--sign', '-', str(path)], check=True)
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ditto', '-c', '-k', '--norsrc', '--noextattr', '--keepParent', str(app), str(output)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package(args.engine, args.build, args.output)
