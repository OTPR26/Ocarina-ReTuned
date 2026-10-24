#!/usr/bin/env python3
"""Stage neutral Switch link inputs, excluding the user's translated title.

This is an intermediate audit directory, not a release archive. Dependency
notices, source provenance, shader, and identity audits must pass separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(command, *, build, sdk, title, output):
    sdk_alias = sdk.absolute()
    build, sdk, title = build.resolve(), sdk.resolve(), title.resolve()
    if output.exists():
        raise ValueError('Choose a new link-input directory')
    tokens = shlex.split(command)
    compiler = next((i for i, t in enumerate(tokens) if Path(t).name == 'aarch64-none-elf-g++'), None)
    if compiler is None:
        raise ValueError('Expected the Switch compiler link command')
    args = tokens[compiler+1:]
    if '&&' in args:
        args = args[:args.index('&&')]
    if args.count('-o') != 1:
        raise ValueError('Expected one linker output')
    files, recipe, sdk_files = [], [], {}
    title_count = 0
    index = 0
    for index, token in enumerate(args):
        if index and args[index-1] == '-o':
            recipe.append('@OUTPUT@')
            continue
        if token.endswith(('.o', '.a')):
            path = Path(token)
            if not path.is_absolute():
                path = build / path
            path = path.resolve()
            if path == title:
                recipe.append('@TITLE@')
                title_count += 1
            elif path.is_relative_to(sdk):
                recipe.append('@SDK@/' + path.relative_to(sdk).as_posix())
                sdk_files[path.relative_to(sdk).as_posix()] = digest(path)
            else:
                if not path.is_file():
                    raise ValueError('Missing link component: ' + path.name)
                if any(word in path.name.lower() for word in ('whole_aot', 'shard_', 'title_source')):
                    raise ValueError('Generated title component outside the explicit title archive')
                name = f'link/{len(files):03d}-{path.name}'
                files.append((path, name))
                recipe.append('@KIT@/' + name)
        else:
            normalized = token.replace(str(sdk_alias), '@SDK@').replace(str(sdk), '@SDK@')
            if str(build) in normalized or str(Path.home()) in normalized:
                raise ValueError('Unresolved private path in link recipe')
            recipe.append(normalized)
    if title_count != 1 or not files:
        raise ValueError('The title archive must occur exactly once')
    nm = sdk / 'devkitA64/bin/aarch64-none-elf-nm'
    # Inspect defined symbols, so harmless host references to title entry points
    # do not look like bundled game functions.
    symbols = subprocess.run([str(nm), '--defined-only', '-g', *[str(p) for p, _ in files]],
                             text=True, capture_output=True, check=True).stdout
    forbidden = ('RetunedSwitchTitleEntryPoints', 'ExecuteRetunedSwitchTitleFunction',
                 'oot3d_whole_aot_shard_', 'oot3d_a32_generated')
    if any(marker in symbols for marker in forbidden):
        raise ValueError('Generated title symbols found in neutral link inputs')
    output.mkdir(parents=True)
    records = []
    for source, name in files:
        target = output / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        records.append({'path': name, 'sha256': digest(target), 'bytes': target.stat().st_size})
    document = {'schema': 'retuned.switch.link-inputs.v1',
                'title_included': False, 'audit_status': 'INTERMEDIATE_NOT_RELEASE_READY',
                'compiler': 'devkitA64/bin/aarch64-none-elf-g++',
                'sdk_files': sdk_files,
                'arguments': recipe, 'files': records}
    (output / 'link-inputs.json').write_text(json.dumps(document, indent=2)+'\n')
    return document


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'sdk', 'title', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    lines = subprocess.check_output(['ninja', '-C', str(a.build), '-t', 'commands', 'OcarinaReTuned.elf'], text=True).splitlines()
    commands = [line for line in lines if '-o OcarinaReTuned.elf' in line]
    if len(commands) != 1:
        raise ValueError('Cannot identify the exact executable link command')
    r = collect(commands[0], build=a.build, sdk=a.sdk, title=a.title, output=a.output)
    print(f"Staged {len(r['files'])} neutral link inputs; final audits still required.")
