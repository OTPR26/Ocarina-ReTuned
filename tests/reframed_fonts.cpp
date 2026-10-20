#include "oot3d_native_font_coverage.h"
#include <algorithm>
#include <cassert>
#include <vector>

static std::vector<std::uint8_t> Font(std::uint8_t size) {
    std::vector<std::uint8_t> bytes(24 + size * size / 2, 0x88);
    const std::uint8_t header[] = {'Q','B','F','1',1,0,1,0,42,0,0,0,4,size,size,2,42,0,0,0,1,2,3,4};
    std::copy(std::begin(header),std::end(header),bytes.begin());
    return bytes;
}
int main() {
    auto native=Font(32),hd=Font(64);
    const auto original=native;
    Oot3dNativeGame::NativeFontCoverage coverage;
    std::string error;
    assert(coverage.Load(native,hd,&error));
    assert(coverage.LogicalWidth()==32 && coverage.LogicalHeight()==32);
    assert(coverage.Density()==2 && coverage.Glyph(24).size()==64*64);
    assert(native==original);
    hd.pop_back();
    assert(!coverage.Load(native,hd,&error));
}
