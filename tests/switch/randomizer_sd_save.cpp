#include "save_store.h"
#include <cassert>
#include <filesystem>
using namespace RetunedRandomizer;
int main(int argc, char** argv) {
    assert(argc == 2);
    const std::filesystem::path dir = argv[1];
    const std::string seed(64, 'a'), runtime(64, 'b');
    Bytes first(0x14dc, 1), second(0x14dc, 2), extended(1244, 3);
    SaveStore store(dir, seed, runtime, extended.size(), true);
    store.Commit(0, first, extended);
    store.Commit(0, second, extended);
    const auto save = dir / "native/save00.bin";
    const auto previous = save.string() + ".previous";
    std::filesystem::rename(save, previous);
    SaveStore recovered(dir, seed, runtime, extended.size(), false);
    assert(std::filesystem::file_size(save) == second.size());
    assert(recovered.Load(0, second) == extended);
    assert(!std::filesystem::exists(previous));
    std::filesystem::copy_file(save, previous);
    SaveStore reopened(dir, seed, runtime, extended.size(), false);
    assert(!std::filesystem::exists(previous));
    assert(reopened.Load(0, first) == extended);
}
