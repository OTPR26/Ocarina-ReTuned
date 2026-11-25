#pragma once
#include "save_store.h"
#include <array>

namespace RetunedRandomizer {
enum class RunStatus { Empty, Ready, Unavailable };
struct RunSlot {
    RunStatus status = RunStatus::Empty;
    std::string seed, preset, seedHash, runtimeHash, error;
    std::size_t extendedSize = 0;
    std::filesystem::path profile;
};

// Each menu slot owns one seed and a separate native/extended save profile.
// The guest uses save slot zero within that profile, not the menu slot number.
struct RunSave {
    unsigned slot;
    Bytes native, extended;
};
class RunCatalog {
public:
    explicit RunCatalog(const std::filesystem::path& appData);
    std::array<RunSlot, 3> List() const;
    RunSlot Read(unsigned slot) const;
    RunSlot Create(unsigned slot, const std::string& seedJson,
                   const std::string& runtimeHash, std::size_t extendedSize,
                   bool allowDevelopmentSeed = false);
    RunSlot Restore(unsigned slot, const std::string& seedJson,
                    const std::string& runtimeHash, std::size_t extendedSize,
                    const std::vector<RunSave>& saves, const Bytes& system,
                    bool allowDevelopmentSeed = false);
    RunSlot Select(unsigned slot, const std::string& preparedRuntimeHash) const;
private:
    std::filesystem::path SlotPath(unsigned slot) const;
    std::filesystem::path root_;
};
}
