#!/usr/bin/env python3
"""Prepare a private iOS/tvOS IPA on a Mac from the owner's ROM and signing profile.

The neutral host template contains no game. The resulting IPA includes locally
generated game data and must stay private; this command never installs or uploads it.
"""
import argparse
import filecmp
import hashlib
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from rom_setup import RomSetup, SetupError, load_kit
from player_models.export import add_arguments as add_model_arguments, prepared_models


def output(*args):
    return subprocess.check_output(list(map(str, args)), text=True, stderr=subprocess.STDOUT)


def apple_title_flags(platform):
    sdk, system = {'ios': ('iphoneos', 'iOS'), 'tvos': ('appletvos', 'tvOS')}[platform]
    return ['-DCMAKE_SYSTEM_NAME=' + system, '-DCMAKE_OSX_SYSROOT=' + sdk,
            '-DCMAKE_OSX_ARCHITECTURES=arm64', '-DCMAKE_OSX_DEPLOYMENT_TARGET=17.0',
            '-DRETUNED_REPRODUCIBLE_PATHS=ON']


def check_apple_module(library, platform):
    if output('lipo', '-archs', library).strip() != 'arm64':
        raise ValueError('Apple title must contain only arm64 code')
    build = output('xcrun', 'vtool', '-show-build', library)
    expected = 'IOS' if platform == 'ios' else 'TVOS'
    platforms = [line.split()[-1] for line in build.splitlines() if line.strip().startswith('platform ')]
    if platforms != [expected]:
        raise ValueError('Title module targets the wrong Apple platform')
    exports = {line.split()[-1] for line in output('xcrun', 'nm', '-gU', library).splitlines() if line.split()}
    if not {'_triaevum_title_aot_query', '_triaevum_title_whole_aot_query'} <= exports:
        raise ValueError('Apple title is missing its public ABI entry points')


class AppleRomSetup(RomSetup):
    def __init__(self, *, apple_platform, **options):
        super().__init__(**options)
        self.apple_platform = apple_platform
        self.native_abi_verified = False

    def compile_title(self, work, generated):
        # Execute the ABI query in a native Mac build of the exact same generated
        # source before cross-compiling. An iOS dylib cannot be dlopened on macOS.
        native = super().compile_title(work, generated)
        super().verify_title(native)
        self.native_abi_verified = True
        build = work / 'apple-build'
        project = Path(__file__).resolve().parents[2]
        args = [self.cmake, '-S', project / 'tools/native/title', '-B', build, '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', *apple_title_flags(self.apple_platform),
                '-DRETUNED_RUNTIME_SOURCE=' + str(self.engine),
                '-DTRIAEVUM_TRANSLATED_TITLE_DIR=' + str(generated)]
        # Only the neutral header location crosses from the Mac kit. Its Mac SDK
        # or compiler options must never override the explicit device target.
        args.extend(value for value in self.cmake_args if value.startswith('-DRETUNED_JSON_INCLUDE_DIR='))
        self.run(args)
        self.run([self.cmake, '--build', build, '--parallel', str(self.jobs)])
        return build / 'triaevum_title_aot.dylib'

    def verify_title(self, library):
        if not self.native_abi_verified:
            raise SetupError('The native ABI verification has not completed')
        check_apple_module(library, self.apple_platform)


def signing_entitlements(profile, identifier, platform):
    required_platform = 'iOS' if platform == 'ios' else 'tvOS'
    if required_platform not in profile.get('Platform', []):
        raise ValueError('Provisioning profile targets the wrong Apple platform')
    entitlements = dict(profile['Entitlements'])
    application = entitlements.get('application-identifier', '')
    prefix, _, suffix = application.partition('.')
    if not prefix or suffix not in (identifier, '*'):
        raise ValueError('Provisioning profile does not permit this app identifier')
    entitlements['application-identifier'] = prefix + '.' + identifier
    groups = entitlements.get('keychain-access-groups')
    if groups is not None:
        entitlements['keychain-access-groups'] = [group.replace(prefix + '.*', prefix + '.' + identifier) for group in groups]
    # Profiles may authorize several environments, but the app signature must
    # select one. Prefer development for a development profile so local Apple
    # builds continue to use the same save database as the Mac app.
    cloud_key = 'com.apple.developer.icloud-container-environment'
    environments = entitlements.get(cloud_key)
    if environments is not None:
        choices = environments if isinstance(environments, list) else [environments]
        if not choices or any(value not in ('Development', 'Production') for value in choices):
            raise ValueError('Provisioning profile has an invalid iCloud environment')
        preferred = 'Development' if entitlements.get('get-task-allow') else 'Production'
        entitlements[cloud_key] = preferred if preferred in choices else choices[0]
    # Keep the profile's authorized containers and services.
    return entitlements


def private_documents(installation, randomizer_test=False):
    manifest = json.loads((installation / 'process-manifest.json').read_text())
    manifest['source'].update(code_bin_path='@BUNDLE@/PrivateGame/code.bin',
        exheader_path='@BUNDLE@/PrivateGame/exheader.bin', romfs_image_path='@BUNDLE@/PrivateGame/romfs.bin')
    profile = {'format': 'oot3d_native_game_launch_profile_v1', 'arguments': [
        '--a32-process-manifest', '@DATA@/process-manifest.json',
        '--resource-root', '@BUNDLE@/PrivateGame',
        '--title-plugin', '@BUNDLE@/Frameworks/triaevum_title_aot.framework/triaevum_title_aot',
        '--renderer', 'nri', '--ui-profile', 'reframed',
        '--config', '@DATA@/config/native-game.json', '--controls-config', '@DATA@/config/controls.json',
        '--save-data', '@DATA@/saves', '--renderer-cache-directory', '@DATA@/cache',
        '--gameplay-timing', 'native30_no_interpolation', '--presentation-rate', '30',
        '--width', '1280', '--height', '720', '--output', '@DATA@/logs/native-summary.json']}
    if randomizer_test:
        proof = manifest['randomizer_proof']
        seed = installation / 'seed.json'
        if (proof.get('seed_file') != 'seed.json' or not proof.get('seed_layout')
                or hashlib.sha256(seed.read_bytes()).hexdigest() != proof.get('seed_sha256')
                or hashlib.sha256((installation / 'code.bin').read_bytes()).hexdigest()
                != manifest['source']['code_bin_sha256']):
            raise ValueError('The private Randomizer seed and image must match the prepared framework')
        args = profile['arguments']
        args[args.index('--save-data') + 1] = '@DATA@/randomizer/bootstrap'
    return manifest, profile


def stage_randomizer_resources(private, installation, identifier):
    alternate = private / 'Randomizer'
    alternate_manifest, _ = private_documents(installation, randomizer_test=True)
    if (identifier != 'io.github.otpr26.ocarinaretuned.randomizer-test'
            and alternate_manifest['randomizer_proof'].get('activation_allowed') is not True):
        raise ValueError('This Randomizer image is limited to the isolated test host')
    alternate.mkdir()
    for key, name in [('code_bin_path','code.bin'), ('exheader_path','exheader.bin'), ('romfs_image_path','romfs.bin')]:
        source = installation / name
        if not filecmp.cmp(private / name, source, shallow=False):
            shutil.copyfile(source, alternate / name)
            alternate_manifest['source'][key] = '@BUNDLE@/PrivateGame/Randomizer/' + name
    shutil.copyfile(installation / 'seed.json', alternate / 'seed.json')
    (alternate / 'process-manifest.json').write_text(json.dumps(alternate_manifest))
    return alternate_manifest


def embed_title(app, library, name, identifier, platform):
    title = app / 'Frameworks' / (name + '.framework')
    title.mkdir(parents=True)
    shutil.copyfile(library, title / name)
    subprocess.run(['install_name_tool', '-id', f'@rpath/{name}.framework/{name}',
                    str(title / name)], check=True)
    (title / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier': identifier, 'CFBundleExecutable': name,
        'CFBundleName': 'Ocarina ReTuned Game', 'CFBundlePackageType': 'FMWK', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.1.0', 'MinimumOSVersion': '17.0',
        'CFBundleSupportedPlatforms': ['iPhoneOS' if platform == 'ios' else 'AppleTVOS']}))
    return title / name


def assemble(installation, template, platform, provisioning, identity, destination, controller_db,
             *, randomizer_test=False, randomizer_installation=None):
    installation, template, destination = map(Path, (installation, template, destination))
    if destination.exists() or destination.is_symlink() or destination.suffix.lower() != '.ipa':
        raise ValueError('Choose a new .ipa output file')
    if (template / 'PrivateGame').exists() or (template / 'Frameworks/triaevum_title_aot.framework').exists():
        raise ValueError('Use a neutral Apple host template without private game data')
    info = plistlib.loads((template / 'Info.plist').read_bytes())
    if randomizer_installation:
        if randomizer_test:
            raise ValueError('Choose either a combined app or a Randomizer-only test')
        randomizer_installation = Path(randomizer_installation)
        randomizer_library = randomizer_installation / 'triaevum_title_aot.dylib'
        check_apple_module(randomizer_library, platform)
    if randomizer_installation and not (template / 'randomizer-launcher-v1').is_file():
        raise ValueError('The Apple host template does not support both game modes')
    if randomizer_test and info['CFBundleIdentifier'] != 'io.github.otpr26.ocarinaretuned.randomizer-test':
        raise ValueError('Use the isolated Randomizer test host')
    profile = plistlib.loads(subprocess.check_output(['security', 'cms', '-D', '-i', str(provisioning)]))
    entitlements = signing_entitlements(profile, info['CFBundleIdentifier'], platform)
    identities = output('security', 'find-identity', '-v', '-p', 'codesigning')
    allowed = {hashlib.sha1(cert).hexdigest().upper() for cert in profile['DeveloperCertificates']}
    if identity.upper() not in allowed or identity.upper() not in identities:
        raise ValueError('Choose an installed signing identity permitted by the profile')
    library = installation / 'triaevum_title_aot.dylib'
    check_apple_module(library, platform)
    manifest, launch = private_documents(installation, randomizer_test)
    if randomizer_installation and "randomizer_proof" in manifest:
        raise ValueError("Start Game requires a normal prepared installation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='retuned-apple-', dir=destination.parent) as temporary:
        root = Path(temporary)
        app = root / 'Payload/OcarinaReTuned.app'
        app.parent.mkdir()
        shutil.copytree(template, app, symlinks=True)
        private = app / 'PrivateGame'
        private.mkdir()
        for name in ('code.bin', 'exheader.bin', 'romfs.bin', 'font_coverage.zip'):
            shutil.copyfile(installation / name, private / name)
        if randomizer_test:
            shutil.copyfile(installation / 'seed.json', private / 'seed.json')
        shutil.copytree(installation / 'lower-equipment', private / 'lower-equipment')
        shutil.copyfile(controller_db, private / 'gamecontrollerdb.txt')
        for name, data in (('process-manifest.json', manifest), ('native-launch.json', launch)):
            (private / name).write_text(json.dumps(data, indent=2) + '\n')
        title = embed_title(app, library, 'triaevum_title_aot', info['CFBundleIdentifier'] + '.title', platform)
        if randomizer_installation:
            alternate_manifest = stage_randomizer_resources(private, randomizer_installation, info['CFBundleIdentifier'])
            randomized_title = embed_title(app, randomizer_library, 'retuned_randomizer',
                info['CFBundleIdentifier'] + '.randomizer', platform)
        shutil.copyfile(provisioning, app / 'embedded.mobileprovision')
        entitlement_file = root / 'entitlements.plist'
        entitlement_file.write_bytes(plistlib.dumps(entitlements))
        for framework in sorted((app / 'Frameworks').glob('*.framework')):
            subprocess.run(['codesign', '--force', '--sign', identity, str(framework)], check=True)
        if randomizer_test or randomizer_installation:
            bound_manifest = alternate_manifest if randomizer_installation else manifest
            bound_title = randomized_title if randomizer_installation else title
            proof = bound_manifest['randomizer_proof']
            layout = json.dumps(proof['seed_layout'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            binding = {
                'format': 'retuned-randomizer-module-v2',
                'seed_layout_sha256': hashlib.sha256(layout.encode()).hexdigest(),
                'code_sha256': bound_manifest['source']['code_bin_sha256'],
                'module_sha256': hashlib.sha256(bound_title.read_bytes()).hexdigest(),
            }
            # A signed framework is sealed. Store the binding in the outer app.
            (private / 'randomizer-framework.json').write_text(json.dumps(binding) + '\n')
        subprocess.run(['codesign', '--force', '--sign', identity, '--entitlements', str(entitlement_file),
                        '--generate-entitlement-der', str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        archive = root / 'private.ipa'
        subprocess.run(['ditto', '-c', '-k', '--norsrc', '--noextattr', '--keepParent', str(app.parent), str(archive)], check=True)
        # Exclusive final output preserves any earlier package, including a
        # destination created while compilation/signing was in progress.
        with destination.open('xb') as target, archive.open('rb') as source:
            shutil.copyfileobj(source, target)
    return {'platform': platform, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'bytes': destination.stat().st_size, 'private_local_artifact': True,
            'redistributable': False, 'signature': 'deep/strict PASS'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kit', 'rom', 'data-root', 'template', 'provisioning', 'output', 'controller-db'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--host', type=Path, help='Mac neutral host for native ABI checks')
    parser.add_argument('--platform', choices=('ios', 'tvos'), required=True)
    parser.add_argument('--identity', required=True, help='Installed signing certificate SHA-1, not a password')
    parser.add_argument('--jobs', type=int, default=2)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--randomizer', action='store_true', help='Prepare the Randomizer from the same ROM before signing')
    mode.add_argument('--randomizer-installation', type=Path, help='Prepared Randomizer installation to bundle alongside the normal game')
    add_model_arguments(parser)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Apple device preparation requires macOS and Xcode')
    setup = AppleRomSetup(apple_platform=args.platform, **load_kit(args.kit, args.host),
        jobs=args.jobs, progress=lambda event: print(json.dumps(event), flush=True))
    if args.randomizer and not (args.template/'randomizer-launcher-v1').is_file():
        parser.error('Choose a host with Randomizer launcher support')
    installation = setup.prepare(args.rom, args.data_root)
    with prepared_models(installation, child=args.child_model, adult=args.adult_model) as exported, tempfile.TemporaryDirectory(dir=args.data_root) as temporary:
        if args.randomizer:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'randomizer'))
            from prepare_rom import build_title
            from stage_runtime import stage_runtime
            kit = args.kit.resolve()
            headers = kit.parent/json.loads(kit.read_text())['json_include']
            work = Path(temporary)
            result = build_title(args.rom, kit, setup, args.platform+'-arm64', work,
                                 dict(json_headers=headers))
            staged = stage_runtime(result['manifest'], result['module'], work/'runtime-store')
            manifest_path = Path(staged['manifest'])
            manifest = json.loads(manifest_path.read_text())
            alternate = work/'alternate'
            alternate.mkdir()
            for key, name in [('code_bin_path','code.bin'), ('romfs_image_path','romfs.bin'),
                              ('exheader_path','exheader.bin')]:
                os.link(manifest_path.parent/manifest['source'][key], alternate/name)
            os.link(staged['module'], alternate/'triaevum_title_aot.dylib')
            shutil.copyfile(manifest_path, alternate/'process-manifest.json')
            shutil.copyfile(manifest_path.parent/'seed.json', alternate/'seed.json')
            args.randomizer_installation = alternate
        receipt = assemble(exported, args.template, args.platform, args.provisioning,
            args.identity, args.output, args.controller_db, randomizer_installation=args.randomizer_installation)
    args.output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Private IPA created locally. Keep it private; no upload or installation was performed.')


if __name__ == '__main__':
    main()
