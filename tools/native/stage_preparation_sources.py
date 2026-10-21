#!/usr/bin/env python3
"""Stage a small, pinned preparation source tree without generated game code.

Compiler SDKs and the project's separately audited HUD patch are added by their
platform packagers. This tool never reads a ROM or translated title directory.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile

from rom_setup import RUNTIME_REVISION, digest

A32 = 'tools/oot3d/native_a32_runtime/'
HOST = 'tools/oot3d/native_game_runtime/'
RELEASE = 'tools/triaevum_release/'
# Dependency closure of the generic support library, its ABI and the plugin
# adapter. No translated title functions, shader tables or game resources.
NATIVE = [
    A32 + name for name in (
        'oot3d_aot_architectural_state.h', 'oot3d_native_a32_vfp_fast.h',
        'oot3d_native_a32_vfp_ops.cpp', 'oot3d_native_a32_vfp_ops.h',
        'upstream/recomp/a32_runtime.h', 'upstream/recomp/a32_vfp_binary64.cpp',
        'upstream/recomp/a32_vfp_binary64.h', 'upstream/recomp/a32_vfp_scalar.cpp',
        'upstream/recomp/a32_vfp_scalar.h', 'upstream/recomp/a32_vfp_transport.cpp',
        'upstream/recomp/a32_vfp_transport.h')
] + [HOST + name for name in (
    'oot3d_native_a32_memory.cpp', 'oot3d_native_a32_memory.h',
    'oot3d_native_a32_memory_bus_defaults.cpp', 'oot3d_native_whole_aot_runtime.h',
    'triaevum_title_aot_abi.h', 'triaevum_title_whole_aot_abi.h',
    'triaevum_title_whole_aot_plugin.cpp')]
TRANSLATORS = [RELEASE + name for name in (
    'ctr_rom.py', 'input_copy_adapter.py', 'oot3d_region_assets.py', 'common.py',
    'input_coverage/recipes/adapters/oot3d-usa-ef210566-copies.json',
    'cmake/TitleSupport.cmake', 'cmake/TranslatedTitleSources.cmake')
] + [A32 + name for name in (
    'generate_aot.py', 'build_process_manifest.py', 'whole_aot_program.py',
    'whole_aot_cpp.py', 'whole_aot_optimization_ir.py', 'whole_aot_memory_regions.py')
] + [A32 + 'upstream/src/oot3d_pack/' + name for name in (
    'a32_cpp_aot.py', 'arm_decode.py', 'arm_ir.py', 'arm_lift.py',
    'arm_softfloat.py', 'arm_softfloat64.py')]
METADATA = {
    A32 + 'upstream/analysis/codebin_function_inventory.csv':
        {'profile', 'entry', 'end', 'size', 'name', 'memory_block'},
    A32 + 'upstream/analysis/codebin_callable_boundary_residue_audit_166.csv':
        {'entry', 'classification'},
    A32 + 'runtime_discovered_entries.csv': {'entry', 'size', 'name'},
}
NOTICES = ('LICENSE', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md')


def sanitize_csv(source, destination, keep):
    with source.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if fields is None or not keep.issubset(fields):
            raise ValueError('Preparation metadata schema changed')
        rows = [{key: row.get(key, '') if key in keep else '' for key in fields}
                for row in reader]
    # The supplemental-entry writer requires a provenance column, but its
    # original developer notes and instruction summaries are unnecessary.
    if 'evidence' in fields and 'entry' in keep:
        for row in rows:
            row['evidence'] = 'reviewed_entry_boundary'
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def stage(engine, output):
    engine, output = Path(engine).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Refusing to replace an existing preparation tree')
    revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != RUNTIME_REVISION:
        raise ValueError('Preparation source revision does not match the app')
    external = A32 + 'whole_aot_functions.json'
    selected = [*NATIVE, *TRANSLATORS, *METADATA, external, *NOTICES]
    originals = {}
    contents = {}
    for name in selected:
        expected = subprocess.check_output(['git', '-C', str(engine), 'show', revision + ':' + name])
        contents[name] = expected
        originals[name] = hashlib.sha256(expected).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.preparation-sources-', dir=output.parent) as temporary:
        staged = Path(temporary) / 'engine'
        staged.mkdir()
        for name in (*NATIVE, *TRANSLATORS, *NOTICES):
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents[name])
        for name, keep in METADATA.items():
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents[name])
            sanitize_csv(target, target, keep)
        overrides = json.loads(contents[external])['external_functions']
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reframed'))
        from apply_native_port import apply_translation_support
        apply_translation_support(staged)
        # Only ABI override declarations, never the original function selection.
        (staged / external).write_text(json.dumps({'external_functions': overrides}, indent=2) + '\n')
        files = {p.relative_to(staged).as_posix(): digest(p) for p in sorted(staged.rglob('*')) if p.is_file()}
        manifest = {'format': 'retuned_preparation_runtime_v1', 'source_revision': revision,
                    'files': files, 'upstream_files': originals,
                    'local_patches': {name: digest(Path(__file__).resolve().parents[2] / name)
                        for name in ('tools/reframed/apply_native_port.py', 'tools/reframed/query_memory.cpp.inc')},
                    'source': 'https://github.com/coccofresco/TriAevum/tree/' + revision}
        (staged / 'preparation-runtime.json').write_text(json.dumps(manifest, indent=2) + '\n')
        staged.rename(output)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    result = stage(options.engine, options.output)
    print('Staged', len(result['files']), 'pinned preparation source files; no ROM or generated title read.')
