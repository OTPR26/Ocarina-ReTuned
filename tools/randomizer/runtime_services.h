#pragma once
#include "save_store.h"
#include <array>
#include <functional>
#include <optional>

namespace RetunedRandomizer {
struct GuestMemory {
    std::function<Bytes(std::uint32_t,std::size_t)> read;
    std::function<void(std::uint32_t,std::span<const std::uint8_t>)> write;
};
// Activated only for the isolated, fixed-seed process. Never attached to an
// ordinary game. Exceptions must become host faults, not silent guest resumes.
class RuntimeServices {
public:
    RuntimeServices(SaveStore& store, GuestMemory memory, std::uint32_t extendedAddress,
                    std::size_t extendedSize,
                    std::function<Bytes(unsigned)> readNative);
    bool Handle(std::uint32_t svc, std::array<std::uint32_t,16>& registers);
    void CommitNativeWrite(unsigned slot, std::uint64_t offset,
                           std::span<const std::uint8_t> native);
private:
    Bytes Read(std::uint32_t address,std::size_t length) const;
    SaveStore& store_;
    GuestMemory memory_;
    std::uint32_t extendedAddress_;
    std::size_t extendedSize_;
    std::function<Bytes(unsigned)> readNative_;
    std::optional<Bytes> beforeInit_;
    bool extendedInitialized_=false;
};
}
