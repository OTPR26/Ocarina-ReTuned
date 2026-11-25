#include "run_catalog.h"
#include <triaevum/sha256.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>

namespace RetunedRandomizer {
namespace {
constexpr std::size_t MaxSeedBytes = 8 * 1024 * 1024;
std::string Hash(const std::string& text) {
    static constexpr char hex[] = "0123456789abcdef";
    std::string out;
    for (auto b : triaevum::module::detail::Sha256(std::span(
             reinterpret_cast<const std::uint8_t*>(text.data()), text.size()))) {
        out += hex[b >> 4]; out += hex[b & 15];
    }
    return out;
}
std::string ReadFile(const std::filesystem::path& path, std::size_t limit) {
    if (std::filesystem::is_symlink(path) || !std::filesystem::is_regular_file(path) ||
        std::filesystem::file_size(path) > limit)
        throw std::runtime_error("Missing or invalid randomizer run file");
    std::ifstream in(path, std::ios::binary);
    in.exceptions(std::ios::badbit);
    return {std::istreambuf_iterator<char>(in), {}};
}
void WriteFile(const std::filesystem::path& path, const std::string& text) {
    std::ofstream out(path, std::ios::binary);
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out << text;
    out.close();
}
nlohmann::json Seed(const std::string& text) {
    if (text.size() > MaxSeedBytes) throw std::runtime_error("Seed is too large");
    auto seed = nlohmann::json::parse(text);
    if (seed.at("format") != "retuned-seed-proof-v1" ||
        seed.at("preset") != "original-glitchless-proof-v1" ||
        seed.at("generator_revision") != "40703bf55b05ab2dda0933a5c5007730b05cebe2" ||
        seed.at("upstream_revision") != "d695cf5ad78dc1990da200af601b054860d707b8")
        throw std::runtime_error("Unsupported seed rules or generator version");
    const auto value = seed.at("seed").get<std::string>();
    if (value.empty() || value.size() > 128 || value.find_first_of("\r\n\t") != std::string::npos)
        throw std::runtime_error("Invalid seed name");
    return seed;
}
}
RunCatalog::RunCatalog(const std::filesystem::path& appData) {
    if (!std::filesystem::is_directory(appData))
        throw std::runtime_error("Application data directory is missing");
    root_ = std::filesystem::canonical(appData) / "randomizer-runs";
    if (std::filesystem::is_symlink(root_))
        throw std::runtime_error("Randomizer directory must not be a link");
    std::filesystem::create_directory(root_);
}
std::filesystem::path RunCatalog::SlotPath(unsigned slot) const {
    if (slot >= 3) throw std::out_of_range("Randomizer slot must be 0, 1, or 2");
    return root_ / ("slot-" + std::to_string(slot + 1));
}
RunSlot RunCatalog::Read(unsigned slot) const {
    const auto path = SlotPath(slot);
    RunSlot result;
    if (!std::filesystem::exists(path) && !std::filesystem::is_symlink(path)) return result;
    result.status = RunStatus::Unavailable;
    try {
        if (std::filesystem::is_symlink(path) || !std::filesystem::is_directory(path))
            throw std::runtime_error("Invalid randomizer slot directory");
        const auto run = nlohmann::json::parse(ReadFile(path / "run.json", 16384));
        const auto text = ReadFile(path / "seed.json", MaxSeedBytes);
        const auto seed = Seed(text);
        if (run.at("format") != "retuned-run-v1" || run.at("seed_sha256") != Hash(text))
            throw std::runtime_error("Randomizer seed identity mismatch");
        result.seed = seed.at("seed"); result.preset = seed.at("preset");
        result.seedHash = run.at("seed_sha256"); result.runtimeHash = run.at("runtime_sha256");
        result.extendedSize = run.at("extended_save_size");
        result.profile = path / "profile";
        SaveStore checked(result.profile, result.seedHash, result.runtimeHash, result.extendedSize, false);
        result.status = RunStatus::Ready;
    } catch (const std::exception&) {
        result.error = "Run is incomplete or incompatible. Its files have been preserved.";
    }
    return result;
}
std::array<RunSlot, 3> RunCatalog::List() const {
    return {Read(0), Read(1), Read(2)};
}
RunSlot RunCatalog::Create(unsigned slot, const std::string& text,
                          const std::string& runtimeHash, std::size_t extendedSize,
                          bool allowDevelopmentSeed) {
    return Restore(slot,text,runtimeHash,extendedSize,{}, {},allowDevelopmentSeed);
}
RunSlot RunCatalog::Restore(unsigned slot, const std::string& text,
                           const std::string& runtimeHash, std::size_t extendedSize,
                           const std::vector<RunSave>& saves, const Bytes& system,
                           bool allowDevelopmentSeed) {
    const auto path = SlotPath(slot);
    const auto seed = Seed(text);
    if(runtimeHash.size()!=64 || runtimeHash.find_first_not_of("0123456789abcdef")!=std::string::npos ||
       extendedSize!=1244 || (!system.empty() && system.size()!=34))
        throw std::runtime_error("Invalid randomizer save identity or ABI");
    unsigned occupied=0;
    for(const auto& save:saves) {
        if(save.slot>=3 || (occupied & (1u<<save.slot)) || save.native.size()!=0x14dc ||
           save.extended.size()!=extendedSize)throw std::runtime_error("Invalid paired randomizer save");
        occupied|=1u<<save.slot;
    }
    if (!seed.at("runtime_ready").get<bool>() && !allowDevelopmentSeed)
        throw std::runtime_error("Development seed is not enabled for normal gameplay");
    // Exclusive directory creation reserves the slot across concurrent creators.
    // An interrupted reservation remains unavailable; never silently overwrite it.
    if (!std::filesystem::create_directory(path))
        throw std::runtime_error("Randomizer slot is already occupied");
    const auto hash = Hash(text);
    SaveStore profile(path / "profile", hash, runtimeHash, extendedSize, true);
    WriteFile(path / "seed.json", text);
    for(const auto& save:saves)profile.Commit(save.slot,save.native,save.extended);
    if(!system.empty()) {
        std::filesystem::create_directory(path/"profile/native");
        WriteFile(path/"profile/native/system.dat",std::string(system.begin(),system.end()));
    }
    nlohmann::json run{{"format", "retuned-run-v1"}, {"seed_sha256", hash},
        {"runtime_sha256", runtimeHash}, {"extended_save_size", extendedSize}};
    WriteFile(path / "run.json.partial", run.dump(2) + "\n");
    std::filesystem::rename(path / "run.json.partial", path / "run.json");
    auto result = Read(slot);
    if (result.status != RunStatus::Ready)
        throw std::runtime_error("Could not verify the new randomizer run; files preserved");
    return result;
}
RunSlot RunCatalog::Select(unsigned slot, const std::string& preparedRuntimeHash) const {
    auto run = Read(slot);
    if (run.status != RunStatus::Ready)
        throw std::runtime_error("Randomizer slot is not ready");
    if (run.runtimeHash != preparedRuntimeHash)
        throw std::runtime_error("This run requires its matching prepared runtime");
    return run;
}
}
