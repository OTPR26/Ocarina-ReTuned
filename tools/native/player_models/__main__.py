"""Import a model into a prepared game after closing its gameplay session."""
import argparse
from .install import change

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', required=True, help='Prepared game data directory')
parser.add_argument('--age', required=True, choices=('child', 'adult'))
source = parser.add_mutually_exclusive_group(required=True)
source.add_argument('--model', help='Local PAK or ZOBJ')
source.add_argument('--restore', action='store_true')
source.add_argument('--use-imported', action='store_true')
parser.add_argument('--entry', help='Model member in a multi-model PAK')
args = parser.parse_args()
change(args.data, age=args.age, package=args.model, entry=args.entry, use_imported=args.use_imported, progress=print)
print('Player model ready. Reopen Ocarina ReTuned to use it.')
