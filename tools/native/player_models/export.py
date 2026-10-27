"""Add model PAKs to a private Apple/Switch export without changing its source."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import shutil
import tempfile

from prepare_ui_assets import RomFs
from .install import ACTORS, MAX_ACTOR, digest
from .reader import require


def add_arguments(parser):
    for age in ACTORS:
        parser.add_argument('--' + age + '-model', type=Path,
                            help='Optional human-rig OoT PAK or ZOBJ for ' + age + ' Link')


@contextmanager
def prepared_models(installation, *, child=None, adult=None):
    installation = Path(installation)
    packages = {age: package for age, package in (('child', child), ('adult', adult)) if package is not None}
    if not packages:
        yield installation
        return
    from .convert import convert_actor
    rom = RomFs(installation / 'romfs.bin')
    replacements, models = {}, {}
    for age, package in packages.items():
        converted, report = convert_actor(rom.read(ACTORS[age]), package, age=age)
        require(0 < len(converted) <= MAX_ACTOR, 'Converted player model is too large')
        replacements[ACTORS[age]] = converted
        models[age] = {'name': str(report.get('source_name', 'Imported model'))[:256],
                       'converted_sha256': digest(converted)}
    with tempfile.TemporaryDirectory(prefix='.model-export-', dir=installation.parent) as temporary:
        destination = Path(temporary)
        # These files are the preparation output, never saves or user settings.
        for name in ('code.bin', 'exheader.bin', 'font_coverage.zip',
                     'triaevum_title_aot.dylib', 'libretuned_switch_title.a'):
            source = installation / name
            if source.is_file():
                require(not source.is_symlink(), 'Linked preparation component')
                shutil.copyfile(source, destination / name)
        equipment = installation / 'lower-equipment'
        if equipment.is_dir():
            require(not equipment.is_symlink() and not any(p.is_symlink() for p in equipment.rglob('*')),
                    'Linked equipment resource')
            shutil.copytree(equipment, destination / 'lower-equipment')
        rom.write_replacements(destination / 'romfs.bin', replacements)
        manifest = json.loads((installation / 'process-manifest.json').read_text())
        manifest = copy.deepcopy(manifest)
        manifest['source'].update(romfs_image_path=str(destination / 'romfs.bin'),
            romfs_image_file_size=(destination / 'romfs.bin').stat().st_size,
            romfs_service_offset=0, romfs_service_size=(destination / 'romfs.bin').stat().st_size)
        manifest['exported_player_models'] = models
        # Desktop import-bank paths cannot be used on the target device.
        manifest.pop('player_models', None)
        manifest.pop('available_player_models', None)
        (destination / 'process-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        yield destination
