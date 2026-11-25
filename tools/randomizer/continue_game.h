#pragma once
#include <cstdint>
#include <stdexcept>

namespace RetunedRandomizer {
// Canonical EUR image: FileSelect_Update phase 3 is the loaded slot list;
// Let the occupied-slot transition build its action layout before starting
// phase 10, which fades and calls FileSelect_LoadFileSlot.
class ContinueGame {
public:
    explicit ContinueGame(bool enabled, bool create = false): pending(enabled), create_(create) {}
    template<class Memory> bool Update(std::uint32_t pc, Memory& memory) {
        if(!pending || pc!=0x0042f9a8) return false;
        std::uint32_t phase=0,valid=0,entry=0,load=0;
        if(!memory.Read32(0x00504fb0,&phase)) fail();
        if(waitingForActions_) {
            if(phase!=8)return false;
            if(!memory.Read32(0x0055bea8,&valid) || valid!=1)fail();
            if(!memory.Write32(0x00504fb8,0) || !memory.Write32(0x00504fc8,0) ||
               !memory.Write32(0x00504fb0,10))fail();
            pending=false;return true;
        }
        if(phase!=3) return false;
        if(!memory.Read32(0x0055bea8,&valid) ||
           !memory.Read32(0x0042f9a8,&entry) || !memory.Read32(0x0044737c,&load)) fail();
        if(waitingForSave_ && valid==0) return false;
        if(valid!=(create_ ? 0u : 1u) || entry!=0xe92d4ff0 || load!=0xe92d47f0) fail();
        if(!memory.Write32(0x0055b5b4,1) ||
           !memory.Write32(0x00504fac,0xffffffff) ||
           !memory.Write32(0x00504ff4,0))fail();
        if(create_) {
            // Native empty-slot selection enters name creation via phase 5.
            // Match its animation state; native code initializes and saves the file.
            for(unsigned i=0;i<3;++i) {
                if(!memory.Write32(0x0055b610+i*4,0xc2a00000) ||
                   !memory.Write32(0x0055b61c+i*4,0)) fail();
            }
            if(!memory.Write32(0x00504fe8,0x42400000) ||
               !memory.Write32(0x00504ff0,0x41400000)) fail();
        }
        if(!memory.Write32(0x00504fb4,0) || // This run owns guest file zero.
           !memory.Write32(0x00504fc8,0) || // Native fade starts at frame zero.
           !memory.Write32(0x00504fb0,create_ ? 5 : 4)) fail();
        if(create_) { create_=false; waitingForSave_=true; }
        else waitingForActions_=true;
        return true;
    }
private:
    bool pending;
    bool create_;
    bool waitingForSave_ = false;
    bool waitingForActions_ = false;
    [[noreturn]] static void fail() { throw std::runtime_error("Randomizer Continue: native save or load contract is invalid"); }
};
}
