"""Region-specific input plans for the shared native runtime."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from preparation_cache import fingerprint
from prepare_ui_assets import RomFs

CANONICAL_CODE = '16a6b0aa4c4784680220a6f780f7f8a73cfb205557aa9f9f0e705179e0613220'
NORMALIZED_ROMFS = {
    'USA': 'dae620379c805e96a6187c212dc2b177cf5fdb0c184d526a06ebaeeaa481aa56',
    'EUR': '32058530b627ef3ca591a404f924a05957af28cda71b036cb472558c77bb8c76',
}


def input_plan(pins, region):
    if region not in NORMALIZED_ROMFS:
        raise ValueError('This ROM region does not yet have a native preparation adapter.')
    matches = [entry for entry in pins['inputs'] if entry['region'] == region]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous regional input identity.')
    entry = matches[0]
    expected = {'canonical-code.bin': CANONICAL_CODE,
                'romfs.bin': NORMALIZED_ROMFS[region],
                'inputs/exheader.bin': entry['exheader']['sha256']}
    key = fingerprint({'format': 'verified-regional-inputs-v1', 'input': entry,
                       'expected': expected, 'extractor': pins['extractor_sha256'],
                       'source_revision': pins['source_revision']})
    keys = [key]
    if region == 'USA':
        # Existing installations predate regional cache keys. Verify their exact
        # hashes before reuse, without making owners select the ROM again.
        legacy_pins = {**pins, 'inputs': [entry]}
        keys.append(fingerprint({'format': 'verified-inputs-v1', 'code': CANONICAL_CODE,
                                 'romfs': NORMALIZED_ROMFS['USA'], 'pins': legacy_pins}))
    return keys, expected


def active_region(profile_root):
    profile = Path(profile_root) / 'native-launch.json'
    if not profile.exists():
        return 'USA'
    document = json.loads(profile.read_text())
    if not isinstance(document, dict):
        raise ValueError('Invalid existing launch profile; preserving it.')
    region = document.get('native_input_region', 'USA')
    if region not in NORMALIZED_ROMFS:
        raise ValueError('Existing game uses an unsupported native input region.')
    return region


def level3_view(source, destination):
    """Remove the IVFC wrapper without modifying regional resource payloads."""
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file() or destination.exists() or destination.is_symlink():
        raise ValueError('Resource preparation requires a regular input and a new output.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.regional-romfs-', dir=destination.parent) as temporary:
        output = Path(temporary) / 'romfs.bin'
        with source.open('rb') as stream, output.open('xb') as target:
            stream.seek(0x1000 if stream.read(4) == b'IVFC' else 0)
            shutil.copyfileobj(stream, target, 4 * 1024 * 1024)
        RomFs(output)
        output.rename(destination)


def normalize(inputs, work, region, *, copy_adapter, usa_resources, recipe):
    inputs, work = Path(inputs), Path(work)
    if region == 'USA':
        copy_adapter.normalize_file(inputs / 'code.bin', work / 'canonical-code.bin', recipe)
        usa_resources.normalize_romfs(inputs / 'romfs.bin', work / 'romfs.bin')
    elif region == 'EUR':
        source = inputs / 'code.bin'
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != CANONICAL_CODE:
            raise ValueError('European executable does not match the native runtime.')
        with (work / 'canonical-code.bin').open('xb') as output, source.open('rb') as stream:
            shutil.copyfileobj(stream, output)
        level3_view(inputs / 'romfs.bin', work / 'romfs.bin')
    else:
        raise ValueError('Unsupported native input region.')
