"""Exercise the pinned NRI destructor helper before and after its correction."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--nri-source', required=True, type=Path)
parser.add_argument('--compiler', default='c++')
parser.add_argument('--cmake', default='cmake')
args = parser.parse_args()
project = Path(__file__).resolve().parents[2]
fixture = r'''
#include <new>
#include <stdexcept>
struct AllocationCallbacks { void (*Free)(void*, void*); void* userArg; };
static int freed = 0, destroyed = 0;
static bool alive = true;
static void FreeObject(void*, void*) { ++freed; }
struct DeviceBase {
    AllocationCallbacks callbacks{FreeObject, nullptr};
    const AllocationCallbacks& GetAllocationCallbacks() { return callbacks; }
};
static DeviceBase device;
struct Object {
    ~Object() { alive = false; ++destroyed; }
    DeviceBase& GetDevice() {
        if (!alive) throw std::runtime_error("GetDevice after destruction");
        return device;
    }
};
@HELPER@
int main() {
    alignas(Object) unsigned char storage[sizeof(Object)];
    Object* object = new (storage) Object;
    try { Destroy<Object>(nullptr); Destroy(object); }
    catch (const std::runtime_error&) { return 7; }
    return freed == 1 && destroyed == 1 ? 0 : 8;
}
'''


def exercise(root, directory, name):
    source = (root / 'Source/Shared/DeviceBase.h').read_text()
    start = source.index('template <typename T>\ninline void Destroy(T* object)')
    end = source.index('\n} // namespace nri', start)
    cpp = directory / (name + '.cpp')
    cpp.write_text(fixture.replace('@HELPER@', source[start:end]))
    binary = directory / name
    subprocess.run([args.compiler, '-std=c++20', '-O0', str(cpp), '-o', str(binary)], check=True)
    return subprocess.run([str(binary)]).returncode


with tempfile.TemporaryDirectory(prefix='retuned-nri-lifetime-') as temporary:
    directory = Path(temporary)
    root = directory / 'nri'
    header = root / 'Source/Shared/DeviceBase.h'
    header.parent.mkdir(parents=True)
    shutil.copy2(args.nri_source / 'Source/Shared/DeviceBase.h', header)
    if exercise(root, directory, 'original') != 7:
        raise SystemExit('Expected original helper to access the destroyed object')
    patch = project / 'tools/native/nri_destroy_lifetime.cmake'
    for _ in range(2):
        subprocess.run([args.cmake, '-DNRI_SOURCE_DIR=' + str(root), '-P', str(patch)], check=True)
    if exercise(root, directory, 'corrected'):
        raise SystemExit('Corrected helper failed destruction/free ordering')
    print('NRI lifetime: original fails, correction passes, repeated patch is safe')
