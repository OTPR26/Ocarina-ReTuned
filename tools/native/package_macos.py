#!/usr/bin/env python3
"""Bundle a neutral ARM64 runtime; title code and game data stay on the user's Mac."""
import argparse
from audit_neutral_shaders import verify as verify_neutral_shaders
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
from runtime_notices import copy_runtime_donor_notices
from macos_deployment import check_bundle, version_tuple


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def package(engine, build, output, identity="-", entitlements=None, profile=None, private_kit=None, minimum_macos='13.4'):
    engine, build, output = Path(engine).resolve(), Path(build).resolve(), Path(output).resolve()
    version_tuple(minimum_macos)
    if output.exists():
        raise ValueError('Refusing to overwrite an existing package.')
    if entitlements and (identity == "-" or not profile):
        raise ValueError("iCloud entitlements require a real signing identity and matching provisioning profile.")
    if private_kit is not None:
        private_root = (Path(__file__).resolve().parents[2]/'work/private').resolve()
        private_kit = Path(private_kit).resolve()
        if os.environ.get('GITHUB_ACTIONS') or not private_kit.is_relative_to(private_root) or not output.is_relative_to(private_root):
            raise ValueError('Private preparation test kits and their packages must stay local.')
        kit = json.loads((private_kit/'kit.json').read_text())
        if kit.get('format') != 'retuned_rom_preparation_kit_v1':
            raise ValueError('Unsupported private preparation test kit')
        for path in private_kit.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(private_kit):
                raise ValueError('Preparation test kit has an external symlink')
    signing = ['--entitlements',str(Path(entitlements).resolve()),'--generate-entitlement-der'] if entitlements else []
    commands = run('ninja', '-C', str(build), '-t', 'commands', 'triaevum_public_runtime')
    forbidden = ('oot3d_whole_aot_shard_', '/oot3d_whole_aot_cpp/', '/oot3d_a32_generated/')
    if any(token in commands for token in forbidden):
        raise ValueError('A neutral build must not compile translated game files.')
    source = build / 'OcarinaReTuned'
    verify_neutral_shaders(engine, source)
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
            'CFBundlePackageType': 'APPL', 'CFBundleVersion': '10',
            'CFBundleShortVersionString': '0.5.6', 'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': minimum_macos}
        (contents / 'Info.plist').write_bytes(plistlib.dumps(metadata))
        notices = resources / 'licenses'
        notices.mkdir()
        shutil.copy2(Path(__file__).resolve().parents[2] / "resources/fonts/LICENSE.txt", notices / "interface-font-OFL.txt")
        shutil.copytree(Path(__file__).resolve().parents[2]/'resources/fonts/interface',notices/'interface-fonts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.ttf'))
        for name in ('LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            shutil.copy2(engine / name, notices / name)
        if (engine / 'LICENSES').is_dir():
            shutil.copytree(engine / 'LICENSES', notices / 'runtime-notices')
        copy_runtime_donor_notices(engine, notices)
        for license_name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt'):
            if (engine / license_name).is_file():
                shutil.copy2(engine / license_name, notices / license_name)
        for formula, license_dir in (('sdl2', 'sdl2-compat'), ('sdl3', 'SDL3')):
            prefix = Path(run('brew', '--prefix', formula))
            license_file = prefix / 'share/licenses' / license_dir / 'LICENSE.txt'
            shutil.copy2(license_file, notices / (formula + '-LICENSE.txt'))
        if private_kit is not None:
            shutil.copytree(private_kit, resources/'setup', symlinks=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            # Sign each nested interpreter/extension before sealing the bundle.
            # These are neutral vendor tools, never generated game modules.
            for path in sorted((resources/'setup').rglob('*')):
                if not path.is_file() or path.is_symlink():
                    continue
                with path.open('rb') as stream:
                    magic = stream.read(4)
                if magic in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'):
                    subprocess.run(['codesign', '--force', '--sign', identity, str(path)], check=True)
            print('Private preparation toolkit staged; this test package must remain local.')
        if profile:
            shutil.copy2(profile, contents/'embedded.provisionprofile')
        deployment = check_bundle(contents, minimum_macos)
        (resources / 'macos-deployment.json').write_text(json.dumps(deployment, indent=2) + '\n')
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
    parser.add_argument('--private-preparation-kit',type=Path)
    parser.add_argument('--minimum-macos',default='13.4')
    args = parser.parse_args()
    package(args.engine, args.build, args.output,args.identity,args.entitlements,args.profile,args.private_preparation_kit,args.minimum_macos)
