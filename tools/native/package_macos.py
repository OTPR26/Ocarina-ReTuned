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


def package(engine, build, output, identity="-", entitlements=None, profile=None):
    engine, build, output = Path(engine).resolve(), Path(build).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite an existing package.')
    if entitlements and (identity == "-" or not profile):
        raise ValueError("iCloud entitlements require a real signing identity and matching provisioning profile.")
    signing = ['--entitlements',str(Path(entitlements).resolve()),'--generate-entitlement-der'] if entitlements else []
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
            dependencies = run('otool', '-L', str(frameworks / 'libSDL3.dylib')).splitlines()[2:]
            if any(not line.strip().split(' ')[0].startswith(('/System/', '/usr/lib/'))
                   for line in dependencies):
                raise ValueError('SDL3 has an unpackaged dependency')
            subprocess.run(['install_name_tool', '-id', '@rpath/libSDL3.dylib',
                            str(frameworks / 'libSDL3.dylib')], check=True)
        vulkan = sorted(frameworks.glob('libvulkan.1.*.dylib'))
        if len(vulkan) != 1:
            raise ValueError('Expected one Vulkan loader.')
        (frameworks / 'libvulkan.1.dylib').symlink_to(vulkan[0].name)
        shutil.copy2(engine / 'runtime/triaevum_resources/gamecontrollerdb.txt', resources)
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
        shutil.copy2(Path(__file__).resolve().parents[2]/'resources/icons/macos/OcarinaReTuned.icns', resources/'OcarinaReTuned.icns')
        metadata = {'CFBundleIconFile':'OcarinaReTuned.icns', 'CFBundleName': 'Ocarina ReTuned', 'CFBundleDisplayName': 'Ocarina ReTuned',
            'CFBundleExecutable': 'retuned-native', 'CFBundleIdentifier': 'io.github.otpr26.ocarinaretuned',
            'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
            'CFBundleShortVersionString': '0.1.0', 'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '13.4'}
        (contents / 'Info.plist').write_bytes(plistlib.dumps(metadata))
        notices = resources / 'licenses'
        notices.mkdir()
        shutil.copy2(Path(__file__).resolve().parents[2] / "resources/fonts/LICENSE.txt", notices / "interface-font-OFL.txt")
        for name in ('LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            shutil.copy2(engine / name, notices / name)
        for license_name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt'):
            if (engine / license_name).is_file():
                shutil.copy2(engine / license_name, notices / license_name)
        for formula, license_dir in (('sdl2', 'sdl2-compat'), ('sdl3', 'SDL3')):
            prefix = Path(run('brew', '--prefix', formula))
            license_file = prefix / 'share/licenses' / license_dir / 'LICENSE.txt'
            shutil.copy2(license_file, notices / (formula + '-LICENSE.txt'))
        if profile:
            shutil.copy2(profile, contents/'embedded.provisionprofile')
        for path in (binary, *frameworks.iterdir()):
            if path.is_file():
                subprocess.run(['codesign', '--force', '--sign', identity, *(signing+['--identifier','io.github.otpr26.ocarinaretuned'] if path==binary else []), str(path)], check=True)
        subprocess.run(['codesign', '--force', '--deep', '--sign', identity, *signing, str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ditto', '-c', '-k', '--norsrc', '--noextattr', '--keepParent', str(app), str(output)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--identity',default='-')
    parser.add_argument('--entitlements',type=Path)
    parser.add_argument('--profile',type=Path)
    args = parser.parse_args()
    package(args.engine, args.build, args.output,args.identity,args.entitlements,args.profile)
