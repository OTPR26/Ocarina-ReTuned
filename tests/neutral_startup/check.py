"""Compile the actual startup call block with a validating preparation backend."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def check(engine, compiler):
    source = (Path(engine) / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_setup.cpp').read_text()
    start = source.index('  if (programPreparation != nullptr &&\n')
    end = source.index('  // Initial preparation:', start)
    block = source[start:end]
    fixture = r'''
#include <span>
#include <stdexcept>
struct Vertex {};
std::span<const Vertex> family;
namespace Oot3dNativeGame {
auto NativePicaVertexProgramFamily() { return family; }
}
struct Backend {
    int calls = 0;
    void PrepareNativePicaPrograms(std::span<const Vertex> vertices) {
        if (vertices.empty()) throw std::runtime_error("no vertex family");
        ++calls;
    }
};
void invoke(Backend* programPreparation, bool parametric, bool alwaysAvailablePrograms) {
    struct { bool PicaParametricTev; } launch{parametric};
@BLOCK@
}
int main() {
    Backend backend;
    try {
        invoke(&backend, true, false);
        invoke(&backend, false, true);
        if (backend.calls != 0) return 3;
        Vertex vertex; family = {&vertex, 1};
        invoke(&backend, false, false);
        if (backend.calls != 0) return 4;
        invoke(&backend, true, false);
        invoke(&backend, false, true);
        invoke(nullptr, true, true);
        if (backend.calls != 2) return 5;
    } catch (...) { return 2; }
}
'''.replace('@BLOCK@', block)
    with tempfile.TemporaryDirectory(prefix='neutral-startup-') as temporary:
        root = Path(temporary)
        cpp = root / 'check.cpp'
        exe = root / ('check.exe' if sys.platform == 'win32' else 'check')
        cpp.write_text(fixture)
        subprocess.run([compiler, '-std=c++20', *(['-static'] if sys.platform == 'win32' else []),
                        str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--compiler', default='c++')
    args = parser.parse_args()
    check(args.engine, args.compiler)
