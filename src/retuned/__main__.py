"""Local preparation tools; no game or patch files are bundled."""
import argparse
import json
from pathlib import Path
from .rom import inspect
from .textures import discover


def main():
    parser = argparse.ArgumentParser(prog='retuned')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('inspect-rom').add_argument('rom', type=Path)
    commands.add_parser('inspect-textures').add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'inspect-rom':
            result = inspect(args.rom)
        else:
            result = {'textures_found': sum(1 for _ in discover(args.folder))}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError):
        parser.exit(1, 'Input could not be validated; no game files or settings were changed.\n')


if __name__ == '__main__':
    main()
