#pragma once
#include <filesystem>
#include <span>
#include <string>
#include <vector>
#include <cstdint>

namespace RetunedRandomizer {
using Bytes = std::vector<std::uint8_t>;
// One store belongs to one seed/runtime pair. The caller owns the guest's save
// directory and must not share it with ordinary gameplay or another process.
class SaveStore {
public:
    SaveStore(std::filesystem::path directory, std::string seedHash,
              std::string runtimeHash, std::size_t extendedSize, bool create);
    void BeforeWrite(unsigned slot, std::span<const std::uint8_t> native,
                     std::span<const std::uint8_t> extended);
    void Commit(unsigned slot, std::span<const std::uint8_t> native,
                std::span<const std::uint8_t> extended);
    Bytes Load(unsigned slot, std::span<const std::uint8_t> native) const;
    const std::filesystem::path& Directory() const { return directory_; }
private:
    std::filesystem::path Record(unsigned slot, std::span<const std::uint8_t> native) const;
    std::filesystem::path directory_;
    Bytes identity_;
    std::size_t extendedSize_;
};
}
