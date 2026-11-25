#pragma once
#include "runtime_services.h"
#include "oot3d_native_a32_ctr_host.h"
#include <fstream>
#include <memory>
#include <stdexcept>

namespace RetunedRandomizer {
// Proof runner only: a dedicated filesystem-backed save directory, one seed,
// no savestates, no profile switching, and no alternate filesystem backend.
inline std::shared_ptr<RuntimeServices> BindHostServices(
        Oot3dNativeGame::NativeA32CtrHostConfig& config,
        Oot3dNativeGame::NativeA32Memory& memory, std::shared_ptr<SaveStore> store,
        std::uint32_t extendedAddress, std::size_t extendedSize) {
    if(config.Filesystem || config.RandomizerSvc || config.WriteRandomizerSave)
        throw std::runtime_error("Randomizer proof requires an unbound filesystem host");
    const auto nativeDirectory=store->Directory()/"native";
    if(std::filesystem::is_symlink(nativeDirectory))throw std::runtime_error("Invalid randomizer native directory");
    std::filesystem::create_directory(nativeDirectory);
    // The store constructor has already verified the seed/runtime identity.
    config.SaveDataDirectory=std::filesystem::canonical(nativeDirectory);
    const auto directory=config.SaveDataDirectory;
    GuestMemory guest{
        [&memory](std::uint32_t at,std::size_t size) {
            Bytes bytes(size);
            if(!memory.ReadBytes(at,bytes))throw std::runtime_error("Randomizer memory read failed");
            return bytes;
        },
        [&memory](std::uint32_t at,std::span<const std::uint8_t> bytes) {
            if(!memory.WriteBytes(at,bytes))throw std::runtime_error("Randomizer memory write failed");
        }};
    auto readNative=[directory](unsigned slot) {
        if(slot>=3)throw std::runtime_error("Invalid native save slot");
        const auto path=directory/("save0"+std::to_string(slot)+".bin");
        if(std::filesystem::is_symlink(path) || std::filesystem::file_size(path)!=0x14dc)
            throw std::runtime_error("Missing or invalid randomized native save");
        Bytes bytes(0x14dc);std::ifstream input(path,std::ios::binary);
        if(!input.read(reinterpret_cast<char*>(bytes.data()),bytes.size()))
            throw std::runtime_error("Cannot read randomized native save");
        return bytes;
    };
    auto services=std::make_shared<RuntimeServices>(*store,std::move(guest),extendedAddress,extendedSize,readNative);
    config.RandomizerSvc=[services,store,&memory](std::uint32_t svc,auto& state,auto& activeMemory) {
        if(&activeMemory!=&memory)throw std::runtime_error("Randomizer guest binding changed");
        std::array<std::uint32_t,16> registers;
        std::copy(std::begin(state.r),std::end(state.r),registers.begin());
        if(!services->Handle(svc,registers))return false;
        std::copy(registers.begin(),registers.end(),std::begin(state.r));
        return true;
    };
    config.WriteRandomizerSave=[services,store,directory](const auto& path,auto offset,auto bytes) -> std::optional<bool> {
        const auto resolved=std::filesystem::weakly_canonical(path);
        if(resolved.parent_path()!=directory || std::filesystem::is_symlink(path))return false;
        for(unsigned slot=0;slot<3;++slot) {
            if(path.filename()=="save0"+std::to_string(slot)+".bin") {
                services->CommitNativeWrite(slot,offset,bytes);return true;
            }
        }
        // Global options and auxiliary native files use the regular file writer.
        return std::nullopt;
    };
    return services;
}
}
