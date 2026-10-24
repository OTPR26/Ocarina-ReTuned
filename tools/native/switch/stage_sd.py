#!/usr/bin/env python3
"""Stage a PRIVATE Switch SD layout from a locally prepared game.

The output contains user game data and must never be included in release assets.
The optional texture directory is supplied by the user, not downloaded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / 'tools/native'))
import prepare_ui_assets
import prepare_open_font


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage(args):
    nro = args.nro.resolve()
    with nro.open('rb') as stream:
        stream.seek(16)
        if stream.read(4) != b'NRO0':
            raise ValueError('Not a Switch NRO')
    manifest = json.loads(args.manifest.read_text())
    source = manifest['source']
    inputs = {}
    for key in ('code_bin', 'exheader', 'romfs_image'):
        path = Path(source[key + '_path'])
        if not path.is_absolute():
            path = args.manifest.parent / path
        if not path.is_file():
            raise ValueError('Missing locally prepared input: ' + key)
        expected = source.get(key + '_sha256')
        if expected and digest(path) != expected:
            raise ValueError('Prepared input integrity mismatch: ' + key)
        inputs[key] = path
    if source['romfs_service_offset'] != 0 or source['romfs_service_size'] != source['romfs_image_file_size']:
        raise ValueError('Switch staging requires a normalized standalone ROMFS image')
    root = args.output.resolve()
    if root.exists():
        raise ValueError('Choose a new output directory to preserve existing SD data')
    game = root / 'switch/oot3dre/game'
    game.mkdir(parents=True)
    install = game.parent
    for directory in ('config', 'savedata', 'cache'):
        (install / directory).mkdir()
    shutil.copyfile(nro, install / 'Ocarina-ReTuned.nro')
    for key, name in (('code_bin', 'code.bin'), ('exheader', 'exheader.bin')):
        shutil.copyfile(inputs[key], game / name)
    ui = prepare_ui_assets.prepare(inputs['romfs_image'], game / 'romfs.bin',
        resources=args.ui_resources, notices_directory=game / 'ui-notices')
    native_font = prepare_ui_assets.RomFs(game / 'romfs.bin').read('message/eu/ltn16.qbf')
    prepare_open_font.pair_styles(native_font, PROJECT / 'resources/fonts', game / 'font_coverage.zip')
    for key, name in (('code_bin', 'code.bin'), ('exheader', 'exheader.bin'), ('romfs_image', 'romfs.bin')):
        source[key + '_path'] = 'sdmc:/switch/oot3dre/game/' + name
        if key + '_sha256' in source:
            source[key + '_sha256'] = digest(game / name)
    source['romfs_image_file_size'] = (game / 'romfs.bin').stat().st_size
    source['romfs_service_size'] = source['romfs_image_file_size']
    (game / 'oot3d_native_process_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shader = args.engine / 'runtime/three_ds_recomp/src/fast/shaders/opengl/default.shader.glsl'
    with zipfile.ZipFile(install / 'resources.o2r', 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(shader, 'shaders/opengl/default.shader.glsl')
    shutil.copyfile(args.engine / 'config/oot3d_controls.switch.json', install / 'config/oot3d_controls.json')
    config = {'Graphics': {'FrameRate': {'Mode': 'Original30'},
                           'TexturePacks': {'Azahar': {'LoadCustomTextures': False,
                               'LoadDirectory': 'sdmc:/switch/oot3dre/textures'}}}}
    if args.mobile_textures:
        pack = args.mobile_textures.resolve()
        if not pack.is_dir() or any(p.is_symlink() for p in pack.rglob('*')):
            raise ValueError('Choose a local texture directory without symbolic links')
        shutil.copytree(pack, install / 'textures')
        config['Graphics']['TexturePacks']['Azahar'] = {
            'LoadCustomTextures': True, 'LoadDirectory': 'sdmc:/switch/oot3dre/textures'}
    (install / 'config/native-game.json').write_text(json.dumps(config, indent=2) + '\n')
    receipt = {'format': 'retuned_private_switch_stage_v1', 'redistributable': False,
        'nro_sha256': digest(nro), 'ui_assets': ui, 'font_styles': ['regular', 'bold'],
        'user_textures_included': bool(args.mobile_textures)}
    (install / 'preparation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Private Switch SD layout prepared; do not upload it.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('nro', 'manifest', 'engine', 'ui-resources', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--mobile-textures', type=Path)
    stage(parser.parse_args())
