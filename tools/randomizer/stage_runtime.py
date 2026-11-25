"""Retain a prepared runtime in private app data, independent of build paths."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import subprocess


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Runtime input must be a regular file')
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def verified_game_image(manifest):
    proof = manifest['randomizer_proof']
    layout = json.dumps(proof.get('seed_layout'), sort_keys=True, separators=(',', ':')).encode()
    return (manifest['source'].get('code_bin_sha256') == '48bbecd347a93ad7247b8285f092b11892188a9ff185604861f9383d53a0a8e1'
            and proof.get('runtime_sha256') in (
                '08d6e235b6d948013b598fe44dd4aa8db9c0cc9756b1df692b59fcb6d125b206',
                '875eb76cd4084d2566ac5e772e2b1282962ad37ae26a8ef29bd100e86bda7010')
            and hashlib.sha256(layout).hexdigest() == '7f4ce7281bd4fda2a8f1161a0d40daec8a9b4bf2e974414e461ce06efe7bde86'
            and proof.get('extended_save_address') == 7359920 and proof.get('extended_save_size') == 1244)


def stage_runtime(manifest_path, module_path, destination, development=False):
    manifest_path, module_path = Path(manifest_path), Path(module_path)
    destination = Path(destination)
    manifest = json.loads(manifest_path.read_text())
    proof = manifest['randomizer_proof']
    if proof['schema'] != 1 or proof['extended_save_size'] != 1244:
        raise ValueError('Unsupported runtime ABI')
    if not development and verified_game_image(manifest):
        proof['activation_allowed'] = True
    if not development and not proof['activation_allowed']:
        raise ValueError('Runtime is not approved for production')
    if 'seed_layout' not in proof or proof['seed_file'] != 'seed.json':
        raise ValueError('A seed-independent runtime is required')
    binding_path = Path(str(module_path) + '.randomizer.json')
    binding = json.loads(binding_path.read_text())
    seed_path = manifest_path.parent / 'seed.json'
    layout = json.dumps(proof['seed_layout'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    if (binding['format'] != 'retuned-randomizer-module-v2' or
            binding['code_sha256'] != manifest['source']['code_bin_sha256'] or
            binding['module_sha256'] != digest(module_path) or
            binding['seed_layout_sha256'] != hashlib.sha256(layout.encode()).hexdigest() or
            proof['seed_sha256'] != digest(seed_path)):
        raise ValueError('Runtime binding does not match its files')
    inputs = {}
    for key, value in manifest['source'].items():
        if key.endswith('_path'):
            path = Path(value)
            if not path.is_absolute():
                path = manifest_path.parent / path
            sha = digest(path)
            expected = manifest['source'].get(key[:-5] + '_sha256')
            if expected is not None and expected != sha:
                raise ValueError('Runtime source digest mismatch')
            inputs[key] = (path, sha)
    if 'code_bin_path' not in inputs:
        raise ValueError('Runtime code is missing')
    destination.mkdir(parents=True, exist_ok=True)
    blobs = destination / 'blobs'
    blobs.mkdir(exist_ok=True)
    # Atomic rename publishes complete files. Existing content is verified and
    # reused; this tool never prunes a runtime that a save might still need.
    def retain(path, sha):
        target = blobs / sha
        if target.exists():
            if digest(target) != sha:
                raise ValueError('Retained runtime content is corrupt')
            return target
        fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=blobs)
        try:
            with os.fdopen(fd, 'wb') as output, path.open('rb') as source:
                shutil.copyfileobj(source, output, 1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            if digest(Path(temporary)) != sha:
                raise ValueError('Runtime input changed while copying')
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return target
    for key, (path, sha) in inputs.items():
        retain(path, sha)
        manifest['source'][key] = '../../blobs/' + sha
    identity = hashlib.sha256(json.dumps({'manifest': manifest, 'binding': binding},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    runtimes = destination / 'runtimes'
    runtimes.mkdir(exist_ok=True)
    final = runtimes / identity
    module_name = 'title' + module_path.suffix
    expected = {'process-manifest.json': json.dumps(manifest, sort_keys=True, indent=2).encode(),
                module_name + '.randomizer.json': binding_path.read_bytes(),
                'seed.json': seed_path.read_bytes()}
    if final.exists():
        if final.is_symlink() or any((final/name).read_bytes() != data for name, data in expected.items()) or digest(final/module_name) != binding['module_sha256']:
            raise ValueError('Retained runtime metadata is corrupt')
    else:
        staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=runtimes))
        try:
            for name, data in expected.items():
                (staging/name).write_bytes(data)
            shutil.copyfile(module_path, staging/module_name)
            if digest(staging/module_name) != binding['module_sha256']:
                raise ValueError('Runtime module changed while copying')
            staging.rename(final)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return {'manifest': str(final/'process-manifest.json'), 'module': str(final/module_name)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--register-mac', action='store_true',
                        help='Select this runtime in the Mac launcher (destination: randomizer/runtime-store)')
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    if args.register_mac and (args.development or args.module.suffix != '.dylib'):
        parser.error('Mac registration requires a production Mac title library')
    if args.register_mac:
        platform = subprocess.check_output(
            ['xcrun', 'vtool', '-arch', 'arm64', '-show-build', str(args.module)], text=True)
        if ['platform', 'MACOS'] not in [line.split() for line in platform.splitlines()]:
            parser.error('The runtime must target arm64 macOS')
    result = stage_runtime(args.manifest, args.module, args.destination, args.development)
    if args.register_mac:
        with tempfile.NamedTemporaryFile(mode='w', dir=args.destination, delete=False) as output:
            json.dump({'runtime': Path(result['manifest']).parent.name}, output)
        try:
            os.replace(output.name, args.destination / 'active.json')
        finally:
            Path(output.name).unlink(missing_ok=True)
    print(json.dumps(result))
