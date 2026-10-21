"""Preserve original notices kept beside compiled donor sources."""
import hashlib
import json
from pathlib import Path
import shutil


DONOR_NOTICES = {
    'libultraship-MIT.txt': 'runtime/three_ds_recomp/LICENSE',
    'Azahar-GPL-2.0.txt': 'tools/oot3d/third_party/azahar_audio/LICENSE.txt',
    'nihstro-BSD-3-Clause.txt': 'tools/oot3d/third_party/azahar_pica/NIHSTRO_LICENSE.txt',
}


def copy_runtime_donor_notices(engine, notices):
    engine, notices = Path(engine), Path(notices)
    # Validate the complete required set before changing the staged package.
    for relative in DONOR_NOTICES.values():
        source = engine / relative
        if not source.is_file() or source.is_symlink() or not source.read_bytes().strip():
            raise ValueError('Missing original runtime donor notice: ' + relative)
    destination = notices / 'source-donors'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for name, relative in DONOR_NOTICES.items():
        source = engine / relative
        shutil.copy2(source, destination / name)
        records.append({'notice': 'source-donors/' + name, 'engine_source': relative,
                        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    (notices / 'source-donor-notices.json').write_text(json.dumps({
        'schema': 1, 'notices': records,
        'scope': 'Original texts for compiled donor sources; root third-party notices retain attribution. '
                 'This index does not replace corresponding-source requirements.'}, indent=2) + '\n')
