#!/usr/bin/env python3
"""Lower only the explicit, locally prepared program; never use developer inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def validate_resume_sites(program, code, catalog):
    """Reject stale hook catalogs or omitted dynamic return boundaries."""
    observed = json.loads(catalog.read_text())
    if observed.get('format') != 'oot3d_whole_aot_observed_sites_v1':
        raise ValueError('Unsupported resume-site catalog')
    if observed.get('code_sha256') != hashlib.sha256(code.read_bytes()).hexdigest():
        raise ValueError('Resume-site catalog does not match the prepared code')
    translated = json.loads(program.read_text())
    starts = {block['pc'] for block in translated['blocks']}
    if any(int(site['pc'], 16) not in starts for site in observed['sites']):
        raise ValueError('Translation omitted a required dynamic resume site')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'program', 'selection', 'code', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--shards', type=int, default=64)
    parser.add_argument('--shard-strategy', choices=('stable', 'affinity'), default='stable')
    parser.add_argument('--observed-sites', type=Path)
    args = parser.parse_args(argv)
    if args.shards < 1:
        parser.error('--shards must be positive')
    for source in (args.program, args.selection, args.code):
        if not source.is_file():
            parser.error('A local preparation input is missing: ' + source.name)
    if args.observed_sites:
        validate_resume_sites(args.program, args.code, args.observed_sites)
    sys.path.insert(0, str(args.engine / 'tools/oot3d/native_a32_runtime'))
    from whole_aot_cpp import generate
    generate(args.program, args.selection, args.code, args.output,
        shard_count=args.shards, shard_strategy=args.shard_strategy, region_entries=frozenset(),
        memory_entries=frozenset(), local_state=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
