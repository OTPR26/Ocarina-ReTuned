"""Prepare the Randomizer's private base image from a supported cartridge dump."""
import argparse
import json
import sys
import tempfile
import shutil
from pathlib import Path

from prepare_resources import DEFAULT_ARCHIVE, prepare as add_resources
from rom_setup import PROJECT, extract_verified_inputs, input_plan, prepare_reframed_image


def prepare(rom, engine, hud, ips, ui, output, *, input_cache=None, region=None):
    if output.exists():
        raise ValueError('Choose a new Randomizer preparation directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    engine = engine.resolve()
    release = engine / 'tools/triaevum_release'
    sys.path[:0] = [str(engine / 'tools/oot3d/native_a32_runtime'), str(release),
                    str(PROJECT / 'tools/reframed')]
    pins = json.loads((PROJECT / 'resources/native-inputs.json').read_text())
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        work = Path(temp)
        if input_cache is None:
            extract_verified_inputs(engine, rom, work, pins, lambda _, text: print(text, flush=True))
        else:
            keys, expected = input_plan(pins, region)
            if not any(input_cache.restore(key, work, expected) for key in keys):
                raise ValueError('Select your ROM in Game preparation once to refresh the verified inputs.')
        print('Preparing Randomizer artwork and HUD…', flush=True)
        receipt = add_resources(work/'romfs.bin', work/'game.bin', DEFAULT_ARCHIVE, ui)
        (work/'game.bin').replace(work/'romfs.bin')
        image = prepare_reframed_image(engine, work, ips, hud, 'unused', receipt['texture_hash_aliases'])
        stage = work/'prepared'
        image.rename(stage)
        manifest_path = stage/'process-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        # Runtime consumers resolve these paths from the game manifest's directory.
        for field, source in [('romfs_image_path', work/'romfs.bin'),
                              ('exheader_path', work/'inputs/exheader.bin')]:
            source.rename(stage/source.name)
            manifest['source'][field] = str((output/source.name).resolve())
        manifest['source']['code_bin_path'] = str((output/'code.bin').resolve())
        manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
        stage.rename(output)
    return output


def build_title(rom, kit, setup, target, work, target_options, *, input_cache=None, region=None):
    from prepare_run import prepare as compile_title
    from stage_runtime import verified_game_image

    recipe = kit.parent / 'randomizer'
    inputs = {name: recipe/name for name in
              ('hud.elf', 'hud.ips', 'runtime.elf', 'runtime-receipt.json', 'bootstrap.json')}
    if any(path.is_symlink() or not path.is_file() for path in inputs.values()):
        raise ValueError('The preparation kit lacks its matching Randomizer recipe')
    ninja = shutil.which('ninja', path=setup.environment['PATH'])
    if not ninja:
        raise ValueError('Ninja is required to prepare the Randomizer title')
    image = prepare(rom.resolve() if rom else None, setup.engine, inputs['hud.elf'], inputs['hud.ips'],
                    setup.ui_resources, work / 'base', input_cache=input_cache, region=region)
    config = dict(target=target, seed_independent=True, image=image,
                  resource_manifest=image/'process-manifest.json', hud=inputs['hud.elf'],
                  runtime=inputs['runtime.elf'], runtime_receipt=inputs['runtime-receipt.json'],
                  engine=setup.engine, cmake=setup.cmake, ninja=ninja,
                  jobs=setup.jobs, artifacts=work/'artifacts', **target_options)
    result = compile_title(config, inputs['bootstrap.json'])
    manifest = json.loads(Path(result['manifest']).read_text())
    if not verified_game_image(manifest):
        raise ValueError('Prepared Randomizer title does not match the verified game image')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom','engine','hud','ips','ui','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.rom, args.engine, args.hud, args.ips, args.ui, args.output)
