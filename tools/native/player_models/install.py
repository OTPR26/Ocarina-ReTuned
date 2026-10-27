"""Activate local player models without recompiling the native game module."""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from .reader import require

ACTORS = {'child': 'actor/zelda_link_child_new.zar',
          'adult': 'actor/zelda_link_boy_new.zar'}
MAX_ACTOR = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_actor(root, record, field):
    require(not (root / 'player-models').is_symlink(), 'Invalid player-model storage')
    path = Path(record[field])
    require(not path.is_symlink() and path.resolve().is_relative_to((root / 'player-models').resolve()),
            'Invalid installed player-model path')
    require(path.is_file() and 0 < path.stat().st_size <= MAX_ACTOR,
            'Installed player model is missing or too large')
    data = path.read_bytes()
    require(digest(data) == record[field + '_sha256'], 'Installed player-model integrity check failed')
    return data


def profile_manifest(root):
    profile = root / 'native-launch.json'
    require(not profile.is_symlink() and profile.stat().st_size <= 1024 * 1024,
            'Invalid launch profile')
    value = json.loads(profile.read_text())
    args = value.get('arguments')
    require(value.get('format') == 'oot3d_native_game_launch_profile_v1'
            and isinstance(args, list) and all(isinstance(s, str) for s in args),
            'Prepare your game before importing a player model')
    require(args.count('--a32-process-manifest') == 1, 'Invalid game manifest argument')
    index = args.index('--a32-process-manifest') + 1
    require(index < len(args), 'Missing game manifest')
    path = Path(args[index])
    if not path.is_absolute(): path = root / path
    args[index] = str(path.absolute())
    require(not path.is_symlink() and path.stat().st_size <= 8 * 1024 * 1024,
            'Invalid prepared game manifest')
    manifest = json.loads(path.read_text())
    for field in ('code_bin_path', 'exheader_path', 'romfs_image_path'):
        if field in manifest['source']:
            source = Path(manifest['source'][field])
            if not source.is_absolute(): manifest['source'][field] = str((path.parent / source).absolute())
    return value, index, manifest


def selection(manifest, field='player_models'):
    value = manifest.get(field, manifest.get('player_models', {}) if field == 'available_player_models' else {})
    require(isinstance(value, dict) and value.keys() <= ACTORS.keys(), 'Invalid model selection')
    require(all(isinstance(record, dict) for record in value.values()), 'Invalid model selection')
    return copy.deepcopy(value)


def apply_to_preparation(root, source, destination, manifest):
    """Reapply a verified selection to fresh game assets during an app update."""
    from prepare_ui_assets import RomFs
    chosen = selection(manifest)
    if not chosen:
        return {}
    rom = RomFs(source)
    replacements = {}
    for age, record in chosen.items():
        original = read_actor(root, record, 'original')
        require(digest(rom.read(ACTORS[age])) == digest(original),
                'The selected player model needs reimporting for these updated game assets')
        replacements[ACTORS[age]] = read_actor(root, record, 'converted')
    rom.write_replacements(destination, replacements)
    return chosen



def prune_old_romfs(root, keep):
    """Keep current/previous asset images; retain imported model source files."""
    parent = root / 'player-models'
    keep = {path.resolve() for path in keep}
    try:
        for entry in parent.iterdir():
            if (entry.is_symlink() or not entry.is_dir() or entry.resolve() in keep
                    or len(entry.name) != 32 or any(c not in '0123456789abcdef' for c in entry.name)):
                continue
            receipt = entry / 'import.json'
            if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 32768:
                continue
            info = json.loads(receipt.read_text())
            if not isinstance(info, dict) or info.get('format') != 'retuned_player_model_v1':
                continue
            image = entry / 'romfs.bin'
            if image.is_file() and not image.is_symlink(): image.unlink()
    except (OSError, ValueError, TypeError):
        pass  # Cleanup cannot invalidate a completed activation.


def change(root, *, age, package=None, entry=None, use_imported=False, transaction_root=None, progress=lambda message: None):
    """Import or restore one age. Call only after the guest game has stopped.

    The launch profile is the commit point. Model files and the modified RomFS
    stay private on this device; the native title module and save paths are reused.
    """
    from prepare_ui_assets import RomFs
    from rom_setup import installation_transaction, write_json
    require(age in ACTORS, 'Choose child or adult')
    root = Path(root).absolute()
    with installation_transaction(transaction_root or root):
        profile, index, manifest = profile_manifest(root)
        installation = Path(profile["arguments"][index]).parent
        chosen = selection(manifest)
        available = selection(manifest, 'available_player_models')
        rom = RomFs(manifest['source']['romfs_image_path'])
        current = rom.read(ACTORS[age])
        previous = chosen.get(age)
        original = read_actor(root, previous, 'original') if previous else current
        if previous:
            require(digest(current) == previous['converted_sha256'],
                    'Current player-model assets do not match the active selection')
        parent = root / 'player-models'
        require(not parent.is_symlink(), 'Invalid player-model storage')
        parent.mkdir(exist_ok=True)
        identity = uuid.uuid4().hex
        stage, target = parent / ('.import-' + identity), parent / identity
        stage.mkdir()
        pending = root / ('.model-launch-' + identity + '.json')
        activated = False
        try:
            # The host resolves font and equipment artwork beside the manifest.
            for name in ('font_coverage.zip', 'ui-assets-receipt.json', 'setup-receipt.json',
                         'lower-equipment', 'ui-notices'):
                source = installation / name
                require(not source.is_symlink(), 'Linked installation resources are unsupported')
                if source.is_dir():
                    files = list(source.rglob('*'))
                    require(len(files) <= 2048 and not any(p.is_symlink() for p in files),
                            'Invalid installation resources')
                    require(sum(p.stat().st_size for p in files if p.is_file()) <= 32 * 1024 * 1024,
                            'Installation resources are too large')
                    shutil.copytree(source, stage / name)
                elif source.is_file():
                    require(source.stat().st_size <= 32 * 1024 * 1024, 'Installation resource is too large')
                    shutil.copyfile(source, stage / name)
            report = {}
            if package is not None:
                from .convert import convert_actor
                progress('Converting player model and textures…')
                converted, report = convert_actor(original, package, age=age, entry=entry)
                require(0 < len(converted) <= MAX_ACTOR, 'Converted player model is too large')
                (stage / 'original.zar').write_bytes(original)
                (stage / 'converted.zar').write_bytes(converted)
                chosen[age] = {field: str(target / (field + '.zar')) for field in ('original', 'converted')}
                chosen[age].update(original_sha256=digest(original), converted_sha256=digest(converted),
                    name=str(report.get('source_name', 'Imported model'))[:256])
                available[age] = copy.deepcopy(chosen[age])
                replacement = converted
            elif use_imported:
                record = available.get(age)
                require(record is not None, 'Import a PAK model for this age first')
                require(digest(original) == record['original_sha256'],
                        'Reimport this model for the current game assets')
                replacement = read_actor(root, record, 'converted')
                chosen[age] = record
            else:
                require(previous is not None, 'This age already uses the original player model')
                chosen.pop(age)
                replacement = original
            progress('Installing player-model assets…')
            rom.write_replacements(stage / 'romfs.bin', {ACTORS[age]: replacement})
            updated = copy.deepcopy(manifest)
            updated['source'].update(romfs_image_path=str(target / 'romfs.bin'),
                romfs_image_file_size=(stage / 'romfs.bin').stat().st_size,
                romfs_service_offset=0, romfs_service_size=(stage / 'romfs.bin').stat().st_size)
            updated['player_models'] = chosen
            updated['available_player_models'] = available
            write_json(stage / 'process-manifest.json', updated)
            write_json(stage / 'import.json', {'format': 'retuned_player_model_v1', 'age': age,
                       'private_local_artifact': True, 'redistributable': False, 'conversion': report})
            profile['arguments'][index] = str(target / 'process-manifest.json')
            write_json(pending, profile)
            with pending.open('r+b') as stream:
                os.fsync(stream.fileno())
            stage.rename(target)
            os.replace(pending, root / 'native-launch.json')
            activated = True
            prune_old_romfs(root, (target, installation))
            return report
        finally:
            pending.unlink(missing_ok=True)
            if stage.exists(): shutil.rmtree(stage)
            if not activated and target.exists(): shutil.rmtree(target)
