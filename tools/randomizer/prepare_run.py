#!/usr/bin/env python3
"""Prepare one private randomizer run using explicitly configured local tools."""
import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from compose_image import main as compose_image

PROJECT = Path(__file__).resolve().parents[2]
APPLE_TARGETS = {'ios-arm64': 'ios', 'tvos-arm64': 'tvos'}


def apple_preparation():
    original_path = sys.path[:]
    sys.path.insert(0, str(PROJECT / 'tools/native'))
    try:
        from prepare_apple_app import apple_title_flags, check_apple_module
        return apple_title_flags, check_apple_module
    finally:
        sys.path[:] = original_path


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path = Path(path)
    partial = path.with_suffix(path.suffix + '.partial')
    partial.write_text(json.dumps(value, indent=2) + '\n')
    partial.replace(path)



def title_target(config):
    target=config.get('target','mac-arm64')
    if target=='mac-arm64':
        flags = ['-DCMAKE_OSX_ARCHITECTURES=arm64']
        if config.get('json_headers'):
            flags.append('-DRETUNED_JSON_INCLUDE_DIR=' + str(Path(config['json_headers']).resolve()))
        return flags, 'triaevum_title_aot.dylib'
    if target in APPLE_TARGETS:
        flags, _ = apple_preparation()
        return [*flags(APPLE_TARGETS[target]),
                '-DRETUNED_JSON_INCLUDE_DIR=' + str(Path(config['json_headers']).resolve())], 'triaevum_title_aot.dylib'
    if target=='switch-arm64':
        sdk = Path(config['switch_sdk']).absolute()
        return ['-DCMAKE_TOOLCHAIN_FILE=' + str(sdk / 'cmake/Switch.cmake'),
                '-DRETUNED_JSON_INCLUDE=' + str(Path(config['json_headers']).resolve())], 'libretuned_switch_title.a'
    if target=='android-arm64':
        ndk=Path(config['ndk']).resolve()
        toolchain=ndk/'build/cmake/android.toolchain.cmake'
        if not toolchain.is_file():raise ValueError('Android NDK toolchain is unavailable')
        return ['-DCMAKE_TOOLCHAIN_FILE='+str(toolchain),'-DANDROID_ABI=arm64-v8a',
                '-DANDROID_PLATFORM=android-29','-DANDROID_STL=c++_shared',
                '-DRETUNED_JSON_INCLUDE_DIR='+str(Path(config['json_headers']).resolve())], 'triaevum_title_aot.so'
    raise ValueError('Unsupported randomizer preparation target')


@contextmanager
def preparation_log(path, android_setup):
    with path.open('a', encoding='utf-8') as log:
        if android_setup is None:
            yield log
            return
        previous = android_setup.log
        android_setup.log = log
        try:
            yield log
        finally:
            android_setup.log = previous


def compile_module(config, work, generated, run, android_setup=None):
    if android_setup is not None:
        if config.get('target') != 'android-arm64':
            raise ValueError('On-device compilation requires the Android target')
        # Use the app's verified SDK, bounded workers, cancellation, and object cache.
        module = android_setup.compile_title(work, generated)
        android_setup.verify_title(module)
        return module
    target_args, module_name = title_target(config)
    switch = config.get('target') == 'switch-arm64'
    project = PROJECT / ('tools/native/switch' if switch else 'tools/native/title')
    source_flags = (['-DRETUNED_ENGINE=' + str(Path(config['engine'])), '-DRETUNED_GENERATED=' + str(generated)]
                    if switch else ['-DRETUNED_RUNTIME_SOURCE=' + str(Path(config['engine'])),
                                    '-DTRIAEVUM_TRANSLATED_TITLE_DIR=' + str(generated)])
    run([config['cmake'], '-S', project, '-B', work/'native', '-G', 'Ninja',
         '-DCMAKE_BUILD_TYPE=Release', *target_args,
         '-DCMAKE_MAKE_PROGRAM='+config['ninja'], *source_flags], 'Configuring native module')
    run([config['cmake'], '--build', work/'native', '--parallel', str(config.get('jobs',4))], 'Building native module')
    module = work / 'native' / module_name
    platform = APPLE_TARGETS.get(config.get('target'))
    if platform:
        _, check = apple_preparation()
        check(module, platform)
    return module


def prepare(config, seed_path, *, android_setup=None, environment=None):
    if android_setup is None:
        return _prepare(config, seed_path, environment=environment)
    if config.get('target') != 'android-arm64':
        raise ValueError('On-device preparation requires the Android target')
    engine = Path(config['engine']).resolve()
    if engine != android_setup.engine:
        raise ValueError('Randomizer preparation must use the Android toolkit engine')
    android_setup.checkpoint('checking', 'Checking local randomizer preparation inputs…')
    android_setup.preflight()

    from preparation_cache import LocalCache, fingerprint

    identity = fingerprint({
        'toolkit': android_setup.preparation_identity,
        'seed_independent': bool(config.get('seed_independent')),
        'sdk': digest(android_setup.sdk / 'sdk.json'),
        'image': digest(Path(config['image']) / 'process-manifest.json'),
        'hud': digest(config['hud']),
        'runtime': digest(config['runtime']),
        'runtime_receipt': digest(config['runtime_receipt']),
        'resources': digest(config['resource_manifest']),
    })
    android_setup.cache = LocalCache(Path(config['artifacts']) / 'android-compiler-cache',
                                    limit=768 * 1024 * 1024)
    original_path = sys.path[:]
    sys.path[:0] = [str(engine / 'tools/oot3d/native_a32_runtime'),
                   str(engine / 'tools/triaevum_release'),
                   str(PROJECT / 'tools/reframed')]
    try:
        return _prepare(config, seed_path, android_setup, identity)
    finally:
        sys.path[:] = original_path


def _prepare(config, seed_path, android_setup=None, toolkit_identity=None, *, environment=None):
    seed_path = seed_path.resolve()
    identity = digest(seed_path)
    if android_setup is None:
        title_target(config)
    artifacts = Path(config['artifacts'])
    if android_setup is not None:
        artifacts = artifacts / 'android-device-arm64' / toolkit_identity
    elif config.get('target', 'mac-arm64') != 'mac-arm64':
        artifacts /= config['target']
    root = artifacts / identity
    root.mkdir(parents=True, exist_ok=True)
    ready = root / 'ready.json'
    if ready.exists():
        # The native launcher rechecks image, seed, and module hashes on every use.
        return json.loads(ready.read_text())
    lock = root / 'preparing.lock'
    if android_setup is None:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    else:
        import fcntl
        fd = os.open(lock, os.O_CREAT | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise
    try:
        # Failed builds remain inspectable. A retry never consumes partial output.
        work = root / ('build-' + uuid.uuid4().hex)
        work.mkdir()
        engine = Path(config['engine'])
        a32 = engine / 'tools/oot3d/native_a32_runtime'
        image, generated = work / 'image', work / 'source'
        env = dict(os.environ if environment is None else environment, PYTHONDONTWRITEBYTECODE='1')
        if config.get('target') == 'switch-arm64':
            sdk = Path(config['switch_sdk']).absolute()
            env.update(DEVKITPRO=str(sdk), DEVKITA64=str(sdk/'devkitA64'))
        def run(args, stage):
            with preparation_log(work / 'build.log', android_setup) as log:
                if android_setup is None:
                    print(stage, flush=True)
                    subprocess.run([str(arg) for arg in args], stdout=log, stderr=subprocess.STDOUT,
                                   check=True, cwd=PROJECT, env=env)
                elif Path(args[1]).name == 'compose_image.py':
                    android_setup.checkpoint('patching', 'Composing the randomizer game image…')
                    with redirect_stdout(log), redirect_stderr(log):
                        compose_image([str(arg) for arg in args[2:]])
                else:
                    android_setup.run(args)

        compose_args = [sys.executable, PROJECT/'tools/randomizer/compose_image.py',
             '--image', config['image'], '--hud', config['hud'], '--runtime', config['runtime'],
             '--receipt', config['runtime_receipt'], '--seed', seed_path, '--output', image]
        if config.get('seed_independent'): compose_args.append('--seed-independent')
        run(compose_args, 'Composing game')
        manifest = json.loads((image/'process-manifest.json').read_text())
        # Keep the verified resource additions and texture aliases from the proof.
        resources = json.loads(Path(config['resource_manifest']).read_text())
        for key in ('romfs_image_path', 'romfs_image_file_size', 'romfs_service_offset', 'romfs_service_size'):
            manifest['source'][key] = resources['source'][key]
        if 'texture_hash_aliases' in resources:
            manifest['texture_hash_aliases'] = resources['texture_hash_aliases']
        write(image/'process-manifest.json', manifest)
        shared = None
        if config.get('seed_independent'):
            shared = artifacts/'shared-runtime'/manifest['source']['code_bin_sha256']/'ready.json'
            if shared.exists():
                cached=json.loads(shared.read_text())
                module=Path(cached['module'])
                binding=json.loads(Path(str(module)+'.randomizer.json').read_text())
                layout_hash=hashlib.sha256(json.dumps(manifest['randomizer_proof']['seed_layout'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if (binding.get('format')!='retuned-randomizer-module-v2' or
                    binding.get('code_sha256')!=manifest['source']['code_bin_sha256'] or
                    binding.get('seed_layout_sha256')!=layout_hash or binding.get('module_sha256')!=digest(module)):
                    raise ValueError('Shared runtime has changed; rebuild it before using another seed')
                result=dict(manifest=str(image/'process-manifest.json'),module=str(module))
                if android_setup is not None:
                    android_setup.checkpoint('verifying', 'Reusing the prepared randomizer game module…')
                else:
                    print('Reusing prepared randomizer runtime', flush=True)
                write(ready, result)
                return result
        run([sys.executable, a32/'whole_aot_program.py' , '--code', image/'code.bin',
             '--inventory', image/'inventory.csv', '--boundary-audit',
             a32/'upstream/analysis/codebin_callable_boundary_residue_audit_166.csv',
             '--observed-sites', image/'observed-sites.json', '--include-instructions',
             '--executable-size', next(s['file_size'] for s in manifest['process']['segments'] if s['name']=='text'),
             '--output', work/'program.json'], 'Translating game')
        program = json.loads((work/'program.json').read_text())
        if any(program['counts'].get(k, 0) for k in ('unclaimed_blocks', 'unresolved_static_edges')):
            raise ValueError('Incomplete game translation')
        external = json.loads((a32/'whole_aot_functions.json').read_text())['external_functions']
        excluded = {f['entry'] for f in external}
        write(work/'selection.json', dict(format='oot3d_whole_aot_function_selection_v1',
            selection_mode='all_lowerable', functions=[dict(entry=f['entry'], name=f['name'],
            reason='randomizer native translation') for f in program['functions'] if f['entry'] not in excluded],
            external_functions=external, performance_exclusions=[], selection_conflicts=[], closure_groups=[]))
        del program
        run([sys.executable, PROJECT/'tools/native/generate_title_sources.py', '--engine', engine,
             '--program', work/'program.json', '--selection', work/'selection.json', '--code', image/'code.bin',
             '--output', generated, '--observed-sites', image/'observed-sites.json', '--shards', '64',
             '--shard-strategy', 'stable'], 'Generating native module')
        if android_setup is not None:
            # Link the randomizer's VFP support before the standard SDK archive.
            shutil.copyfile(a32 / 'upstream/recomp/a32_vfp_binary64.cpp',
                            generated / 'randomizer_vfp_binary64.cpp')
        write(generated/'TITLE_SOURCE_MANIFEST.json', dict(format='triaevum_translated_title_source_v1',
            private_local_artifact=True, redistributable=False,
            files={p.name:digest(p) for p in generated.iterdir() if p.suffix in ('.cpp','.h')}))
        with preparation_log(work / 'build.log', android_setup):
            module = compile_module(config, work, generated, run, android_setup)
        if android_setup is not None:
            android_setup.checkpoint('verifying', 'Verifying the randomizer game module…')
        if not module.is_file():
            raise ValueError('Missing compiled module')
        write(str(module)+'.randomizer.json', dict(format='retuned-randomizer-module-v1',
            seed_sha256=identity, code_sha256=manifest['source']['code_bin_sha256'], module_sha256=digest(module)))
        if shared is not None:
            layout_hash=hashlib.sha256(json.dumps(manifest['randomizer_proof']['seed_layout'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            write(str(module)+'.randomizer.json',dict(format='retuned-randomizer-module-v2',
                seed_layout_sha256=layout_hash,code_sha256=manifest['source']['code_bin_sha256'],module_sha256=digest(module)))
            shared.parent.mkdir(parents=True,exist_ok=True)
            write(shared,dict(module=str(module)))
        result = dict(manifest=str(image/'process-manifest.json'), module=str(module))
        write(ready, result)
        return result
    finally:
        if android_setup is None:
            lock.unlink()
        else:
            os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    result = prepare(config, args.seed)
    if config.get('runtime_store'):
        from stage_runtime import stage_runtime
        result = stage_runtime(result['manifest'], result['module'], config['runtime_store'],
                               development=config.get('allow_development_runtime', False))
    write(args.result, result)
