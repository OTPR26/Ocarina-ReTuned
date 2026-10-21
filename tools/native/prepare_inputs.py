#!/usr/bin/env python3
"""Prepare verified private native inputs from a user-owned cartridge dump."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
from retuned.native_inputs import verify_identity


def prepare(engine, rom, output):
    engine, rom, output = Path(engine).resolve(), Path(rom).resolve(), Path(output).absolute()
    pins = json.loads((PROJECT / 'resources/native-inputs.json').read_text())
    source = 'tools/triaevum_release/ctr_rom.py'
    if (engine / '.git').exists():
        revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != pins['source_revision']:
            raise ValueError('Native extraction source revision does not match the pinned reference.')
        subprocess.run(['git', '-C', str(engine), 'diff', '--exit-code', 'HEAD', '--', source],
                       check=True, stdout=subprocess.DEVNULL)
    # Android carries a verified tools bundle, not a Git client or checkout.
    if hashlib.sha256((engine / source).read_bytes()).hexdigest() != pins['extractor_sha256']:
        raise ValueError('ROM extractor does not match the pinned reference.')
    if output.exists() or output.is_symlink():
        raise ValueError('Native input output already exists; preserving it.')
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('_retuned_ctr_rom', engine / source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='.native-inputs-', dir=output.parent) as temp:
        stage = Path(temp) / 'inputs'
        extracted = module.extract_decrypted_rom(rom, stage)
        identity = {'program_id': f'{extracted.program_id:016X}'}
        for kind in ('code', 'exheader', 'romfs'):
            item = getattr(extracted, kind)
            identity[kind] = {'bytes': item.bytes, 'sha256': item.sha256}
        verified = verify_identity(identity)
        (stage / 'identity.json').write_text(json.dumps({**verified, 'inputs': identity,
            'private_local_artifact': True, 'redistributable': False}, indent=2) + '\n')
        # Refuse an overlapping writer; rename only into a nonexistent destination.
        output.mkdir()
        try:
            for file in stage.iterdir():
                shutil.move(str(file), output / file.name)
        except BaseException:
            shutil.rmtree(output)
            raise
    return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.engine, args.rom, args.output)
        print('Prepared verified ' + result['region'] + ' native inputs locally.')
    except (OSError, ValueError, subprocess.SubprocessError):
        parser.exit(1, 'Native preparation failed; source ROM and existing data were preserved.\n')
