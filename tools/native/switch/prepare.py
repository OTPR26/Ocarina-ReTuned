#!/usr/bin/env python3
"""Prepare a private Switch game locally. Never distribute the output."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rom_setup import RomSetup, SetupError, digest, load_kit
from player_models.export import add_arguments as add_model_arguments, prepared_models

ROOT = Path(__file__).resolve().parent


def checked_file(root, relative):
    part = Path(relative)
    target = (root / part).resolve()
    if part.is_absolute() or '..' in part.parts or not target.is_relative_to(root.resolve()) or not target.is_file():
        raise SetupError('Invalid or missing preparation component')
    return target


def load_link_inputs(root, sdk):
    document = json.loads((root / 'link-inputs.json').read_text())
    if document.get('schema') != 'retuned.switch.link-inputs.v1' or document.get('title_included') is not False:
        raise SetupError('Unsupported Switch link kit')
    for record in document['files']:
        if digest(checked_file(root, record['path'])) != record['sha256']:
            raise SetupError('Switch link component checksum mismatch')
    for name, expected in document['sdk_files'].items():
        if digest(checked_file(sdk, name)) != expected:
            raise SetupError('The Switch SDK libraries do not match this Preview')
    return document


def link_arguments(document, root, sdk, title, output):
    values = {'@KIT@': str(root.resolve()), '@SDK@': str(sdk.absolute()),
              '@TITLE@': str(title.resolve()), '@OUTPUT@': str(output.resolve())}
    result = []
    for token in document['arguments']:
        for marker, value in values.items():
            token = token.replace(marker, value)
        if '@' in token or token in ('&&', ';', '|'):
            raise SetupError('Invalid Switch link recipe')
        result.append(token)
    return result


class SwitchSetup(RomSetup):
    title_shards = 256
    title_shard_strategy = 'affinity'

    def __init__(self, *, sdk, link_kit, json_include, **options):
        self.sdk = Path(sdk).absolute()
        self.link_kit = Path(link_kit).resolve()
        self.json_include = Path(json_include).resolve()
        self.suffix = '.exe' if os.name == 'nt' else ''
        compiler = self.sdk / ('devkitA64/bin/aarch64-none-elf-g++' + self.suffix)
        super().__init__(host=compiler, **options)
        self.environment.update(DEVKITPRO=str(self.sdk), DEVKITA64=str(self.sdk / 'devkitA64'))
        self.environment['PATH'] = str(self.sdk / 'tools/bin') + os.pathsep + self.environment.get('PATH', '')

    def verify_host(self):
        if ' ' in str(self.sdk):
            raise SetupError('Use a Switch SDK path without spaces')
        version = subprocess.check_output([str(self.host), '-dumpfullversion'], env=self.environment, text=True).strip()
        if version != '16.1.0':
            raise SetupError('This Preview requires devkitA64 GCC 16.1.0')
        self.link_recipe = load_link_inputs(self.link_kit, self.sdk)
        for relative in ('cmake/Switch.cmake', 'tools/bin/elf2nro' + self.suffix, 'tools/bin/nacptool' + self.suffix):
            checked_file(self.sdk, relative)

    def compile_title(self, work, generated):
        build = work / 'build'
        self.run([self.cmake, '-S', ROOT, '-B', build, '-G', 'Ninja',
            '-DCMAKE_TOOLCHAIN_FILE=' + str(self.sdk / 'cmake/Switch.cmake'),
            '-DRETUNED_ENGINE=' + str(self.engine), '-DRETUNED_GENERATED=' + str(generated),
            '-DRETUNED_JSON_INCLUDE=' + str(self.json_include)])
        self.run([self.cmake, '--build', build, '--parallel', str(self.jobs)])
        return build / 'libretuned_switch_title.a'

    def verify_title(self, library):
        nm = self.sdk / ('devkitA64/bin/aarch64-none-elf-nm' + self.suffix)
        symbols = subprocess.check_output([str(nm), '--defined-only', '-g', str(library)], text=True, env=self.environment)
        for name in ('RetunedSwitchTitleEntryPoints', 'ExecuteRetunedSwitchTitleFunction'):
            if name not in symbols:
                raise SetupError('Prepared Switch title ABI is incomplete')

    def export_sd(self, installation, output, textures=None, nsp_packer=None, nsp_keys=None):
        if output.exists():
            raise SetupError('Choose a new SD output folder; existing files are preserved')
        self.checkpoint('linking', 'Linking your prepared Switch game…')
        binary = installation / 'OcarinaReTuned.elf'
        self.run([self.host, *link_arguments(self.link_recipe, self.link_kit, self.sdk,
            installation / 'libretuned_switch_title.a', binary)])
        nacp = installation / 'OcarinaReTuned.nacp'
        self.run([self.sdk / ('tools/bin/nacptool' + self.suffix), '--create',
            'Ocarina ReTuned', 'OTPR26', '0.5.8', nacp])
        nro = installation / 'Ocarina-ReTuned.nro'
        self.run([self.sdk / ('tools/bin/elf2nro' + self.suffix), binary, nro,
            '--nacp=' + str(nacp), '--icon=' + str(self.link_kit / 'icon.jpg')])
        self.checkpoint('copying', 'Creating the private SD-card layout…')
        install = output / 'switch/oot3dre'
        game = install / 'game'
        game.mkdir(parents=True)
        for name in ('code.bin', 'exheader.bin', 'romfs.bin', 'font_coverage.zip'):
            shutil.copyfile(installation / name, game / name)
        for directory in ('config', 'savedata', 'cache'):
            (install / directory).mkdir()
        shutil.copyfile(nro, install / nro.name)
        manifest = json.loads((installation / 'process-manifest.json').read_text())
        for key, name in (('code_bin', 'code.bin'), ('exheader', 'exheader.bin'), ('romfs_image', 'romfs.bin')):
            manifest['source'][key + '_path'] = 'sdmc:/switch/oot3dre/game/' + name
        (game / 'oot3d_native_process_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        shutil.copyfile(self.link_kit / 'resources.o2r', install / 'resources.o2r')
        shutil.copyfile(self.link_kit / 'controls.json', install / 'config/oot3d_controls.json')
        config = {'Graphics': {'FrameRate': {'Mode': 'Original30'}, 'TexturePacks': {'Azahar': {
            'LoadCustomTextures': bool(textures), 'LoadDirectory': 'sdmc:/switch/oot3dre/textures'}}}}
        if textures:
            if not textures.is_dir() or any(p.is_symlink() for p in textures.rglob('*')):
                raise SetupError('Choose an extracted mobile texture pack without symbolic links')
            shutil.copytree(textures, install / 'textures')
        (install / 'config/native-game.json').write_text(json.dumps(config, indent=2)+'\n')
        (install / 'PRIVATE-GAME-DATA.txt').write_text('Prepared from your ROM. Do not redistribute this folder or NRO.\n')
        if nsp_packer:
            self.checkpoint('packaging', 'Packaging your private Switch NSP…')
            package = installation / 'nsp-build'
            for name in ('exefs', 'control', 'output', 'temp', 'nca', 'backup'):
                (package / name).mkdir(parents=True)
            self.run([self.sdk / ('tools/bin/elf2nso' + self.suffix), binary, package / 'exefs/main'])
            shutil.copyfile(self.link_kit / 'main.npdm', package / 'exefs/main.npdm')
            shutil.copyfile(nacp, package / 'control/control.nacp')
            shutil.copyfile(self.link_kit / 'icon.jpg', package / 'control/icon_AmericanEnglish.dat')
            command = [nsp_packer, '-k', nsp_keys, '--noromfs', '--nologo',
                '--titleid', '0100f0260a000000', '--titlename', 'Ocarina ReTuned',
                '--titlepublisher', 'OTPR26', '--keygeneration', '1']
            for option, name in (('exefsdir', 'exefs'), ('controldir', 'control'), ('nspdir', 'output'),
                                 ('tempdir', 'temp'), ('ncadir', 'nca'), ('backupdir', 'backup')):
                command.extend(['--' + option, package / name])
            self.run(command, cwd=package)
            shutil.copyfile(package / 'output/0100f0260a000000.nsp', output / 'Ocarina-ReTuned.nsp')
        self.progress({'stage': 'complete', 'message': 'Private Switch SD layout ready: ' + str(output)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kit', 'sdk', 'rom', 'work-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--mobile-textures', type=Path)
    parser.add_argument('--jobs', type=int, default=2)
    add_model_arguments(parser)
    parser.add_argument('--nsp-packer', type=Path, help='Local hacBrewPack executable for optional private NSP creation')
    parser.add_argument('--nsp-keys', type=Path, help='Your own local keys; never copied into the prepared output')
    args = parser.parse_args()
    if args.work_dir.exists() or args.output.exists():
        parser.error('Choose new work and output folders to preserve existing game files')
    if bool(args.nsp_packer) != bool(args.nsp_keys):
        parser.error('--nsp-packer and --nsp-keys must be supplied together')
    kit = args.kit.resolve()
    options = load_kit(kit, host=args.sdk / 'devkitA64/bin/aarch64-none-elf-g++')
    options.pop('host')
    setup = SwitchSetup(sdk=args.sdk, link_kit=kit.parent / 'switch-host', json_include=kit.parent / 'headers',
        **options, jobs=args.jobs, progress=lambda e: print(e['message'], flush=True))
    installation = setup.prepare(args.rom, args.work_dir)
    with prepared_models(installation, child=args.child_model, adult=args.adult_model) as exported:
        setup.export_sd(exported, args.output, args.mobile_textures,
            args.nsp_packer.resolve() if args.nsp_packer else None,
            args.nsp_keys.resolve() if args.nsp_keys else None)
    print('Use full-memory homebrew launching. Never redistribute the prepared game.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
