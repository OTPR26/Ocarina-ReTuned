"""Check aligned ELF pack bytes, paths with spaces, and dependency rebuilding."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cmake', default='cmake')
parser.add_argument('--compiler', default='c++')
args = parser.parse_args()
helper = Path(__file__).resolve().parents[2] / 'tools/native/spirv_pack_elf.cmake'
source = '''#include <span>
#include <cstdint>
namespace Test { namespace {
TRIAEVUM_SPIRV_PACK_EMBED_BEGIN
alignas(16) const unsigned char kPack[] = {0};
TRIAEVUM_SPIRV_PACK_EMBED_END
}
bool verify() {
 if (kPack.size()!=1795 || reinterpret_cast<uintptr_t>(kPack.data()) % 16) return false;
 for(unsigned i=0;i<1792;i++) if(kPack[i] != i%256) return false;
 return kPack[1792]==0 && kPack[1793]==255 && kPack[1794]==1;
}
}
int main(){ return Test::verify() ? 0 : 1; }
'''
with tempfile.TemporaryDirectory(prefix='retuned-pack-check-') as temporary:
    root = Path(temporary)
    (root / 'probe.cpp').write_text(source)
    pack = root / 'pack with spaces.spvpack'
    original = bytes(range(256)) * 7 + b'\x00\xff\x01'
    pack.write_bytes(original)
    (root / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.26)
project(EmbeddingCheck LANGUAGES CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
 message(FATAL_ERROR "Run this ELF embedding check on Linux")
endif()
set(CMAKE_CXX_STANDARD 20)
set(TRIAEVUM_CXX_HAS_EMBED OFF)
include("''' + helper.as_posix() + '''")
add_executable(embedding_probe)
triaevum_add_spirv_pack(embedding_probe "${CMAKE_CURRENT_SOURCE_DIR}/probe.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/pack with spaces.spvpack")
''')
    build = root / 'build'
    subprocess.run([args.cmake, '-S', str(root), '-B', str(build), '-G', 'Ninja',
                    '-DCMAKE_CXX_COMPILER=' + args.compiler], check=True)
    def rebuild():
        subprocess.run([args.cmake, '--build', str(build)], check=True)
    rebuild()
    subprocess.run([str(build / 'embedding_probe')], check=True)
    pack.write_bytes(b'\xff' + original[1:])
    rebuild()
    if subprocess.run([str(build / 'embedding_probe')]).returncode != 1:
        raise SystemExit('Pack dependency was stale after its contents changed')
    pack.write_bytes(original)
    rebuild()
    subprocess.run([str(build / 'embedding_probe')], check=True)
    if list(build.rglob('*.spvpack.inc')):
        raise SystemExit('ELF path unexpectedly generated a C++ byte-literal list')
    print('ELF embedding: exact bytes, 16-byte alignment, and pack-change rebuild PASS')
