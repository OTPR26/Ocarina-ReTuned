"""Move ReFramed's file-selection preview and caption right without resizing."""
from pathlib import Path
import argparse


def apply(root: Path):
    path = root / 'src/single_screen.c'
    source = path.read_text()
    # PICA's rotated viewport Y decreases when logical screen X increases.
    # Eight logical pixels create a gap while retaining the right-hand inset.
    pairs = [('SetViewport(119, -8, 300, 200);',
              'SetViewport(119, -16, 300, 200);', 1),
             ('SetViewport(56, 2, 264, 192);',
              'SetViewport(56, -6, 264, 192);', 2)]
    for before, after, count in pairs:
        if source.count(after) == count and before not in source:
            continue
        if source.count(before) != count or after in source:
            raise ValueError('File-selection viewport context changed')
        source = source.replace(before, after)
    path.write_text(source)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)
