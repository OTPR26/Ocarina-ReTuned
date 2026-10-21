namespace {
std::uint16_t FontU16(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    return bytes[at] | (static_cast<std::uint16_t>(bytes[at+1]) << 8);
}
bool CompatibleFontAllocation(const std::vector<std::uint8_t>& source,
                              const std::vector<std::uint8_t>& replacement) {
    if (source.size() < 16 || replacement.size() < 16 ||
        std::memcmp(source.data(), "QBF1", 4) || std::memcmp(replacement.data(), "QBF1", 4) ||
        source.size() < replacement.size() || FontU16(source,4) != FontU16(replacement,4) ||
        FontU16(source,8) != FontU16(replacement,8) ||
        !std::equal(source.begin()+12,source.begin()+16,replacement.begin()+12)) return false;
    const std::size_t count=FontU16(source,4), glyphs=FontU16(source,6);
    const auto expected=16+count*8+glyphs*static_cast<std::size_t>(source[13])*source[14]/2;
    if (source[12] != 4 || source[15] != 2 || expected != source.size() ||
        16+count*8 > replacement.size()) return false;
    for (std::size_t i=0; i<count; ++i)
        if (FontU16(source,16+i*8) != FontU16(replacement,16+i*8)) return false;
    return true;
}
}

void NativeHdFontRuntime::ObserveLookup(const oot3d::recomp::a32::GuestState& state,
                                       NativeA32Memory& memory) {
    if (!mHasStyleChoices || state.r[0] > UINT32_MAX-4) return;
    std::uint32_t qbf=0;
    if (!memory.Read32(state.r[0]+4,&qbf) || !qbf) return;
    const auto& chosen=mFonts[mSelectedFont].Native;
    const auto* current=memory.GetReadPointer(qbf,chosen.size());
    if (!current || std::memcmp(current,chosen.data(),chosen.size()) == 0) return;
    for (const auto& source : mNativeSources) {
        const auto* bytes=memory.GetReadPointer(qbf,source.size());
        if (bytes && std::memcmp(bytes,source.data(),source.size()) == 0) {
            // Source and destination have identical character/cell geometry;
            // the selected image fits the existing allocation. No ROM writes.
            if (memory.WriteBytes(qbf,chosen)) ++StyleSelections;
            return;
        }
    }
}
