"""Embedded-Python entry point for Android's isolated preparation service."""
import json
import os
from pathlib import Path
import sys


def register_randomizer(kit, internal, profile):
    if not (kit / 'randomizer/runtime.elf').is_file():
        return
    normal = json.loads((profile / 'native-launch.json').read_text())
    root = internal.parent / 'randomizer'
    root.mkdir(exist_ok=True)
    config = dict(app_data=str(root / 'data'), artifacts=str(root / 'artifacts'),
                  runtime_store=str(root / 'runtime-store'), device_preparation=True,
                  normal_arguments=normal['arguments'], input_region=normal['native_input_region'])
    temporary = root / 'runtime.json.partial'
    temporary.write_text(json.dumps(config) + '\n')
    temporary.replace(root / 'runtime.json')


def prepare(kit_path, native_directory, rom_path, internal_root, userdata_root,
            cancel_path, preparation_identity, callback):
    sys.dont_write_bytecode = True
    kit = Path(kit_path)
    os.environ['LIBCAPSTONE_PATH'] = native_directory
    sys.path[:0] = [str(kit / 'project/tools/native/android'),
                   str(kit / 'project/tools/native'), str(kit / 'project/src')]
    from rom_preparation import AndroidRomSetup
    from rom_setup import FileCancellation, SetupCancelled

    def progress(event):
        callback.progressDetailed(event['stage'], event['message'],
                                  event.get('completed', -1), event.get('total', -1))

    try:
        worker = AndroidRomSetup(engine=kit / 'engine', ips=kit / 'hud.ips',
            elf=kit / 'hud.elf', sdk=kit / 'sdk',
            compiler=Path(native_directory) / 'libretuned_clang.so',
            linker=Path(native_directory) / 'libretuned_lld.so',
            runtime_library=Path(native_directory) / 'libc++_shared.so',
            progress=progress, cancel=FileCancellation(cancel_path),
            profile_root=userdata_root, preparation_identity=preparation_identity)
        worker.prepare(rom_path or None, internal_root)
        register_randomizer(kit, Path(internal_root), Path(userdata_root))
        return True
    except SetupCancelled:
        callback.progress('cancelled', 'Setup cancelled. Your ROM and saves are unchanged.')
    except Exception as error:
        callback.progress('error', str(error) or 'Setup could not finish. Your ROM and saves are unchanged.')
    return False


def prepare_randomizer(kit_path, native_directory, root_path, job_path, callback):
    sys.dont_write_bytecode = True
    kit = Path(kit_path)
    root, job = Path(root_path), Path(job_path)
    os.environ['LIBCAPSTONE_PATH'] = native_directory
    sys.path[:0] = [str(kit / 'project' / path) for path in
                   ('tools/native/android', 'tools/native', 'tools/randomizer', 'src')]
    from rom_preparation import AndroidRomSetup
    from rom_setup import FileCancellation, write_json
    from prepare_run import prepare as prepare_run
    from stage_runtime import stage_runtime

    recipe = kit / 'randomizer'
    packaged = (recipe / 'runtime.elf').is_file()
    patches = recipe if packaged else kit
    config = json.loads((root / ('runtime.json' if packaged else 'device-preparation.json')).read_text())
    native = Path(native_directory)
    worker = AndroidRomSetup(
        engine=kit / 'randomizer-engine', ips=patches / 'hud.ips', elf=patches / 'hud.elf', sdk=kit / 'sdk',
        compiler=native / 'libretuned_clang.so', linker=native / 'libretuned_lld.so',
        runtime_library=native / 'libc++_shared.so',
        cancel=FileCancellation(job / 'cancel'),
        preparation_identity=kit.name,
        progress=lambda event: callback.progressDetailed(
            event['stage'], event['message'], event.get('completed', -1), event.get('total', -1)))
    if packaged:
        from preparation_cache import LocalCache, fingerprint
        from prepare_rom import prepare as prepare_base
        region = config['input_region']
        image = root / 'inputs' / fingerprint([kit.name, region])
        if not image.exists():
            worker.checkpoint('patching', 'Preparing the Randomizer from your verified game inputs…')
            prepare_base(None, worker.engine, worker.elf, worker.ips, kit / 'native-ui.zip', image,
                         input_cache=LocalCache(root.parent / 'native-data/verified-inputs'), region=region)
        config = dict(image=str(image), resource_manifest=str(image / 'process-manifest.json'),
                      hud=str(worker.elf), runtime=str(recipe / 'runtime.elf'),
                      runtime_receipt=str(recipe / 'runtime-receipt.json'))
    elif config.get('allow_development_runtime') is not True:
        config['hud'] = str(worker.elf)
    else:
        config.setdefault('hud', str(worker.elf))
    config.update(target='android-arm64', engine=str(worker.engine),
                  artifacts=str(root / 'artifacts'), seed_independent=True)
    result = prepare_run(config, job / 'seed.json', android_setup=worker)
    worker.checkpoint('verifying', 'Retaining the prepared randomizer runtime…')
    result = stage_runtime(result['manifest'], result['module'], root / 'runtime-store',
                           development=bool(config.get('allow_development_runtime', False)))
    worker.checkpoint('verifying', 'Verifying the selected run…')
    write_json(job / 'result.json', result)
