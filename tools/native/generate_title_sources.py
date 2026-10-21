#!/usr/bin/env python3
"""Lower only the explicit, locally prepared program; never use developer inputs."""
import argparse
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'program', 'selection', 'code', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--shards', type=int, default=64)
    args = parser.parse_args(argv)
    if args.shards < 1:
        parser.error('--shards must be positive')
    for source in (args.program, args.selection, args.code):
        if not source.is_file():
            parser.error('A local preparation input is missing: ' + source.name)
    sys.path.insert(0, str(args.engine / 'tools/oot3d/native_a32_runtime'))
    from whole_aot_cpp import generate
    generate(args.program, args.selection, args.code, args.output,
        shard_count=args.shards, shard_strategy='stable', region_entries=frozenset(),
        memory_entries=frozenset(), local_state=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
