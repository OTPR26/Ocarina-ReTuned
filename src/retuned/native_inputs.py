"""Content identities for native translation; cartridge padding is immaterial."""
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2] / 'resources/native-inputs.json'


def verify_identity(identity, catalog=CATALOG):
    for expected in json.loads(Path(catalog).read_text())['inputs']:
        if identity.get('program_id') == expected['program_id'] and all(
            identity.get(kind) == expected[kind] for kind in ('code', 'exheader', 'romfs')
        ):
            return {'region': expected['region'], 'program_id': expected['program_id'],
                    'verified': True, 'validation': 'native_content_v1'}
    raise ValueError('Executable, ExHeader or RomFS does not match a verified native input.')
