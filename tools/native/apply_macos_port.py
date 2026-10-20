#!/usr/bin/env python3
"""Apply the small macOS source fixes against the pinned runtime."""
from pathlib import Path
import argparse
import subprocess

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'


def apply(root):
    root = Path(root)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Runtime revision differs from the tested port baseline.')
    patches = [
        ('runtime/three_ds_recomp/src/fast/backends/gfx_metal_shader.cpp',
         '== SHADER_ID_PICA_TEXTURE_ENV', '== Fast::SHADER_ID_PICA_TEXTURE_ENV'),
        ('runtime/three_ds_recomp/src/fast/oot3d/pica_shader_instrumentation.cpp',
         '    std::from_chars(text.data(), text.data() + text.size(), parsed);',
         '    std::istringstream parser(text);\n    parser.imbue(std::locale::classic());\n    parser >> parsed;'),
    ]
    for relative, before, after in patches:
        path = root / relative
        source = path.read_text()
        if source.count(before) == 1:
            path.write_text(source.replace(before, after))
        elif source.count(after) != 1:
            raise ValueError('macOS source fix context changed: ' + relative)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
