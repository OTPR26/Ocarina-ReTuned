NativeA32Memory::RegionInfo NativeA32Memory::QueryRegion(uint32_t address) const {
    // The CTR application address space ends at 1 GiB. Kernel space is reserved.
    constexpr uint64_t limit = 0x40000000ULL;
    if (address >= limit) return {0x40000000U, 0xC0000000U, 0U, 1U};
    uint64_t begin = 0, end = limit;
    for (const auto& region : mRegions) {
        const uint64_t base = region.BaseAddress;
        const uint64_t stop = base + region.Bytes.size();
        if (address >= base && address < stop) {
            const uint32_t permissions = 1U | (region.Writable ? 2U : 0U) |
                                         (region.Executable ? 4U : 0U);
            const uint32_t state = region.Name.starts_with("shared_memory:") ? 6U :
                                   region.Executable ? 4U : 5U;
            return {region.BaseAddress, static_cast<uint32_t>(region.Bytes.size()), permissions, state};
        }
        if (stop <= address && stop > begin) begin = stop;
        if (base > address && base < end) end = base;
    }
    return {static_cast<uint32_t>(begin), static_cast<uint32_t>(end - begin), 0U, 0U};
}
