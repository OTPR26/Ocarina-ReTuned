#include "ship/config/ConfigPersistence.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
int main(int argc, char** argv) {
    assert(argc == 2);
    namespace fs = std::filesystem;
    const fs::path root(argv[1]);
    fs::create_directories(root);
    const auto target = root / "settings.json";
    auto read = [&] { std::ifstream in(target); return std::string(std::istreambuf_iterator<char>(in), {}); };
    assert(Ship::WriteConfigFileAtomically(target, "first").Success);
    assert(Ship::WriteConfigFileAtomically(target, "second").Success);
    assert(read() == "second");
    assert(!fs::exists(target.string()+".previous"));
    // Simulate interruption after retaining the previous generation.
    fs::rename(target, target.string()+".previous");
    assert(Ship::WriteConfigFileAtomically(target, "third").Success);
    assert(read() == "third");
    // A failed write must leave the installed document untouched.
    assert(!Ship::WriteConfigFileAtomically(root/"absent"/"settings.json", "bad").Success);
    assert(read() == "third");
    fs::remove(target);
}
