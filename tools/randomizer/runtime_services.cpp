#include "runtime_services.h"
#include <algorithm>
#include <stdexcept>

namespace RetunedRandomizer {
namespace {
constexpr std::uint32_t InitStart=0x53ccf4;
constexpr std::uint32_t InitEnd=InitStart+0x1a1*0x44;
void Slot(unsigned slot) {if(slot>=3)throw std::runtime_error("Invalid randomizer slot");}
}
RuntimeServices::RuntimeServices(SaveStore& store,GuestMemory memory,std::uint32_t address,
        std::size_t size,std::function<Bytes(unsigned)> readNative)
    :store_(store),memory_(std::move(memory)),extendedAddress_(address),extendedSize_(size),
      readNative_(std::move(readNative)) {
    if(!memory_.read || !memory_.write || !readNative_ || address<0x680000 ||
       !size || size>1024*1024 || std::uint64_t(address)+size>0x800000)
        throw std::runtime_error("Invalid randomizer service binding");
}
Bytes RuntimeServices::Read(std::uint32_t address,std::size_t size) const {
    auto bytes=memory_.read(address,size);
    if(bytes.size()!=size)throw std::runtime_error("Incomplete randomizer guest read");
    return bytes;
}
bool RuntimeServices::Handle(std::uint32_t svc,std::array<std::uint32_t,16>& r) {
    switch(svc) {
    case 0xfff401:
        if(beforeInit_)throw std::runtime_error("Nested randomizer initialization");
        beforeInit_=Read(InitStart,InitEnd-InitStart);
        return true;
    case 0xfff402: {
        if(!beforeInit_)throw std::runtime_error("Randomizer initialization was not started");
        auto after=Read(InitStart,InitEnd-InitStart);
        // Changed object names invalidate the game's cached archive sizes.
        // This proof never switches back to an ordinary runtime in-process.
        const std::array<std::uint8_t,4> zero{};
        for(unsigned id=0;id<0x1a1;++id) {
            const auto address=0x53ccf4+id*0x44,offset=address-InitStart;
            if(!std::equal(after.begin()+offset,after.begin()+offset+0x40,beforeInit_->begin()+offset))
                memory_.write(address+0x40,zero);
        }
        beforeInit_.reset();return true;
    }
    case 0xfff403: {
        Slot(r[0]);
        // Missing state is an error, even for a native save that looks valid.
        // New-file initialization does not call this until its first save exists.
        auto extended=store_.Load(r[0],readNative_(r[0]));
        if(extended.size()!=extendedSize_)throw std::runtime_error("Extended save ABI mismatch");
        memory_.write(extendedAddress_,extended);extendedInitialized_=true;return true;
    }
    case 0xfff404:
        Slot(r[0]);
        // Called after new-file initialization and also after ordinary writes.
        // The filesystem callback captures bytes while the guest is paused.
        extendedInitialized_=true;return true;
    case 0xfff405:
        // Fixed proof preset uses vanilla prices, so preserve the input price.
        return true;
    case 0xfff40b:
        r[0]=2;return true; // Explicit offline command; multiplayer is disabled.
    default:return false;
    }
}
void RuntimeServices::CommitNativeWrite(unsigned slot,std::uint64_t offset,
                                        std::span<const std::uint8_t> native) {
    Slot(slot);
    if(offset || native.size()!=0x14dc || !extendedInitialized_)
        throw std::runtime_error("Native save precedes extended-state initialization");
    store_.Commit(slot,native,Read(extendedAddress_,extendedSize_));
}
}
