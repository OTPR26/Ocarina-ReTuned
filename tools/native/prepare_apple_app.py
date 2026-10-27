#!/usr/bin/env python3
"""Prepare a private iOS/tvOS IPA on a Mac from the owner's ROM and signing profile.

The neutral host template contains no game. The resulting IPA includes locally
generated game data and must stay private; this command never installs or uploads it.
"""
import argparse
import hashlib
import json
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
        sdk, system = ('iphoneos', 'iOS') if self.apple_platform == 'ios' else ('appletvos', 'tvOS')
        build = work / 'apple-build'
        project = Path(__file__).resolve().parents[2]
        args = [self.cmake, '-S', project / 'tools/native/title', '-B', build, '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_SYSTEM_NAME=' + system,
                '-DCMAKE_OSX_SYSROOT=' + sdk, '-DCMAKE_OSX_ARCHITECTURES=arm64',
                '-DCMAKE_OSX_DEPLOYMENT_TARGET=17.0', '-DRETUNED_REPRODUCIBLE_PATHS=ON',
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


def private_documents(installation):
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
    return manifest, profile


def assemble(installation, template, platform, provisioning, identity, destination, controller_db):
    installation, template, destination = map(Path, (installation, template, destination))
    if destination.exists() or destination.is_symlink() or destination.suffix.lower() != '.ipa':
        raise ValueError('Choose a new .ipa output file')
    if (template / 'PrivateGame').exists() or (template / 'Frameworks/triaevum_title_aot.framework').exists():
        raise ValueError('Use a neutral Apple host template without private game data')
    info = plistlib.loads((template / 'Info.plist').read_bytes())
    profile = plistlib.loads(subprocess.check_output(['security', 'cms', '-D', '-i', str(provisioning)]))
    entitlements = signing_entitlements(profile, info['CFBundleIdentifier'], platform)
    identities = output('security', 'find-identity', '-v', '-p', 'codesigning')
    allowed = {hashlib.sha1(cert).hexdigest().upper() for cert in profile['DeveloperCertificates']}
    if identity.upper() not in allowed or identity.upper() not in identities:
        raise ValueError('Choose an installed signing identity permitted by the profile')
    library = installation / 'triaevum_title_aot.dylib'
    check_apple_module(library, platform)
    manifest, launch = private_documents(installation)
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
        shutil.copytree(installation / 'lower-equipment', private / 'lower-equipment')
        shutil.copyfile(controller_db, private / 'gamecontrollerdb.txt')
        for name, data in (('process-manifest.json', manifest), ('native-launch.json', launch)):
            (private / name).write_text(json.dumps(data, indent=2) + '\n')
        title = app / 'Frameworks/triaevum_title_aot.framework'
        title.mkdir(parents=True)
        shutil.copyfile(library, title / 'triaevum_title_aot')
        subprocess.run(['install_name_tool', '-id', '@rpath/triaevum_title_aot.framework/triaevum_title_aot',
                        str(title / 'triaevum_title_aot')], check=True)
        (title / 'Info.plist').write_bytes(plistlib.dumps({
            'CFBundleIdentifier': info['CFBundleIdentifier'] + '.title', 'CFBundleExecutable': 'triaevum_title_aot',
            'CFBundleName': 'Ocarina ReTuned Game', 'CFBundlePackageType': 'FMWK', 'CFBundleVersion': '1',
            'CFBundleShortVersionString': '0.1.0', 'MinimumOSVersion': '17.0',
            'CFBundleSupportedPlatforms': ['iPhoneOS' if platform == 'ios' else 'AppleTVOS']}))
        shutil.copyfile(provisioning, app / 'embedded.mobileprovision')
        entitlement_file = root / 'entitlements.plist'
        entitlement_file.write_bytes(plistlib.dumps(entitlements))
        for framework in sorted((app / 'Frameworks').glob('*.framework')):
            subprocess.run(['codesign', '--force', '--sign', identity, str(framework)], check=True)
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
    add_model_arguments(parser)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Apple device preparation requires macOS and Xcode')
    setup = AppleRomSetup(apple_platform=args.platform, **load_kit(args.kit, args.host),
        jobs=args.jobs, progress=lambda event: print(json.dumps(event), flush=True))
    installation = setup.prepare(args.rom, args.data_root)
    with prepared_models(installation, child=args.child_model, adult=args.adult_model) as exported:
        receipt = assemble(exported, args.template, args.platform, args.provisioning,
            args.identity, args.output, args.controller_db)
    args.output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Private IPA created locally. Keep it private; no upload or installation was performed.')


if __name__ == '__main__':
    main()
