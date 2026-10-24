// SPDX-License-Identifier: GPL-2.0-or-later
// The Switch NRO has no ELF program-header loader to register PT_GNU_EH_FRAME.
// Resolve the linker's read-only, position-independent unwind index directly.
#include <cstdint>
#include <cstring>
extern "C" const unsigned char __eh_frame_hdr_start[] __attribute__((visibility("hidden")));
struct RetunedDwarfBases { void* text; void* data; void* function; };
namespace {
int32_t ReadSigned(const unsigned char* p) { int32_t v; std::memcpy(&v,p,4); return v; }
uint32_t ReadUnsigned(const unsigned char* p) { uint32_t v; std::memcpy(&v,p,4); return v; }
}
extern "C" const void* __wrap__Unwind_Find_FDE(const void* pc, RetunedDwarfBases* bases) {
    const auto* h = __eh_frame_hdr_start;
    // GNU ld emits version 1, pcrel/sdata4 frame pointer, udata4 count,
    // and datarel/sdata4 binary-search entries for this toolchain.
    if (h[0]!=1 || h[1]!=0x1b || h[2]!=0x03 || h[3]!=0x3b) return nullptr;
    const uintptr_t address = reinterpret_cast<uintptr_t>(pc);
    const uintptr_t base = reinterpret_cast<uintptr_t>(h);
    uint32_t lo=0, hi=ReadUnsigned(h+8);
    while (lo<hi) {
        const uint32_t mid=lo+(hi-lo)/2;
        const uintptr_t begin=base+ReadSigned(h+12+mid*8);
        if (begin<=address) lo=mid+1; else hi=mid;
    }
    if (!lo) return nullptr;
    const auto* entry=h+12+(lo-1)*8;
    const uintptr_t begin=base+ReadSigned(entry);
    const auto* fde=reinterpret_cast<const unsigned char*>(base+ReadSigned(entry+4));
    // FDEs use a 32-bit PC-relative initial location and unsigned extent.
    if (address-begin>=ReadUnsigned(fde+12)) return nullptr;
    bases->text=nullptr;
    bases->data=const_cast<unsigned char*>(h);
    bases->function=reinterpret_cast<void*>(begin);
    return fde;
}
