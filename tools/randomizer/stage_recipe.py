"""Stage the neutral inputs used to prepare a player's local Randomizer module."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from prepare_resources import DEFAULT_ARCHIVE, ARCHIVE_SHA256

RUNTIME = '875eb76cd4084d2566ac5e772e2b1282962ad37ae26a8ef29bd100e86bda7010'
HUD = 'a8ec178ada634e8fbd0d61e3cb6e347cac7db05736da1b350de0916901607793'
IPS = 'f87f809e8ece757fe46ca97c2109401a13aebddfcd13e6bd75c1fba6cdd434cf'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(runtime, receipt, hud, ips, objcopy, generator, output):
    if output.exists():
        raise ValueError('Choose a new recipe directory')
    proof = json.loads(receipt.read_text())
    if (digest(hud) != HUD or digest(ips) != IPS or proof['hud_sha256'] != HUD
            or proof['elf_sha256'] != digest(runtime) or digest(DEFAULT_ARCHIVE) != ARCHIVE_SHA256):
        raise ValueError('The preparation inputs do not match the reviewed Randomizer recipe')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        root = Path(temp)
        result = root/'recipe'
        result.mkdir()
        subprocess.run([objcopy, '--strip-debug', runtime, result/'runtime.elf'], check=True)
        if digest(result/'runtime.elf') != RUNTIME:
            raise ValueError('Unexpected stripped Randomizer runtime')
        proof['elf_sha256'] = RUNTIME
        (result/'runtime-receipt.json').write_text(json.dumps(proof, indent=2)+'\n')
        shutil.copyfile(hud, result/'hud.elf')
        shutil.copyfile(ips, result/'hud.ips')
        subprocess.run([generator, 'ReTuned-bootstrap', root/'bootstrap'], check=True)
        (root/'bootstrap/seed.json').rename(result/'bootstrap.json')
        result.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','receipt','hud','ips','objcopy','generator','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    stage(**vars(parser.parse_args()))
