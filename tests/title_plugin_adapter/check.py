"""Compile the actual native adapter against an ABI-only generated-header fixture."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', type=Path, required=True)
parser.add_argument('--headers', type=Path, required=True)
parser.add_argument('--compiler', default='cl' if sys.platform == 'win32' else 'c++')
options = parser.parse_args()
host = options.engine / 'tools/oot3d/native_game_runtime'
a32 = options.engine / 'tools/oot3d/native_a32_runtime'
includes = [host, a32, a32 / 'upstream', options.headers, Path(__file__).resolve().parent]
source = host / 'triaevum_title_whole_aot_plugin.cpp'
with tempfile.TemporaryDirectory(prefix='retuned-adapter-check-') as temporary:
    output = Path(temporary) / ('adapter.obj' if sys.platform == 'win32' else 'adapter.o')
    if sys.platform == 'win32':
        command = [options.compiler, '/nologo', '/std:c++20', '/EHsc', '/MT', '/c',
            *('/I' + str(path) for path in includes), str(source), '/Fo' + str(output)]
    else:
        command = [options.compiler, '-std=c++20', '-c', *('-I' + str(path) for path in includes),
            str(source), '-o', str(output)]
    raise SystemExit(subprocess.run(command).returncode)
