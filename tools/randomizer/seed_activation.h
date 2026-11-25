#pragma once
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace RetunedRandomizer {
struct SeedWrite { std::uint32_t address; std::vector<std::uint8_t> bytes; };
// Construct the entire plan before touching a fresh guest. Layout comes from
// the prepared runtime, never from an imported seed.
std::vector<SeedWrite> PlanSeedActivation(const nlohmann::json& seed,
                                        const nlohmann::json& layout);
template<class Memory>
void ActivateSeed(Memory& memory, const std::vector<SeedWrite>& writes) {
    // Check every destination before writing. A failed write aborts launch;
    // callers must discard the fresh guest, never continue with partial data.
    for (const auto& write : writes) {
        std::vector<std::uint8_t> original(write.bytes.size());
        if (!memory.ReadBytes(write.address, original))
            throw std::runtime_error("Randomizer seed destination is not mapped");
    }
    for (const auto& write : writes)
        if (!memory.WriteBytes(write.address, write.bytes))
            throw std::runtime_error("Cannot activate randomizer seed");
}
}
