#include "run_catalog.h"
#include "generator.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <chrono>
#include <iostream>

using namespace RetunedRandomizer;
void Check(bool condition) { if (!condition) throw std::runtime_error("Run catalog check failed"); }
template<class F> void Reject(F f) {
    bool rejected = false;
    try { f(); } catch (const std::exception&) { rejected = true; }
    Check(rejected);
}
int main() {
    auto root = std::filesystem::temp_directory_path() /
        ("retuned-run-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    Check(std::filesystem::create_directory(root));
    try {
        std::ofstream(root / "save00.bin") << "ordinary save";
        RunCatalog catalog(root);
        for (const auto& slot : catalog.List()) Check(slot.status == RunStatus::Empty);
        const auto seed = Generate("retuned-proof-001");
        const std::string runtime(64, 'a');
        Reject([&] { catalog.Create(0, seed, runtime, 1244); });
        Check(catalog.Read(0).status == RunStatus::Empty);
        auto slot = catalog.Create(0, seed, runtime, 1244, true);
        Check(slot.status == RunStatus::Ready && slot.seed == "retuned-proof-001");
        Check(catalog.Select(0, runtime).profile == slot.profile);
        Reject([&] { catalog.Select(0, std::string(64, 'b')); });
        Reject([&] { catalog.Create(0, seed, runtime, 1244, true); });
        Reject([&] { catalog.Read(3); });
        auto second = catalog.Create(1, Generate("retuned-proof-002"), runtime, 1244, true);
        Check(second.profile != slot.profile && second.seedHash != slot.seedHash);
        Bytes native(0x14dc), extended(1244, 42);
        SaveStore store(slot.profile, slot.seedHash, runtime, 1244, false);
        store.Commit(0, native, extended);
        RunCatalog reopened(root);
        auto recovered = reopened.Select(0, runtime);
        SaveStore saved(recovered.profile, recovered.seedHash, runtime, 1244, false);
        Check(saved.Load(0, native) == extended);
        Check(!std::filesystem::exists(second.profile / "native/save00.bin"));
        std::filesystem::create_directory(root / "randomizer-runs/slot-3");
        Check(reopened.Read(2).status == RunStatus::Unavailable);
        Reject([&] { reopened.Create(2, seed, runtime, 1244, true); });
        std::ofstream(root / "randomizer-runs/slot-1/seed.json", std::ios::app) << ' ';
        Check(reopened.Read(0).status == RunStatus::Unavailable);
        Reject([&] { reopened.Select(0, runtime); });
        std::string ordinary; std::getline(std::ifstream(root / "save00.bin"), ordinary);
        Check(ordinary == "ordinary save");
        std::filesystem::remove_all(root);
        std::cerr << "Slot isolation, reload, occupied slots, corruption, and runtime mismatch passed.\n";
    } catch (...) { std::filesystem::remove_all(root); throw; }
}
