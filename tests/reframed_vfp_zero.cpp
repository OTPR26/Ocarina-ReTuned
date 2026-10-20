#include "a32_vfp_binary64.h"
#include <cassert>
#include <bit>
#include <cstdint>

using namespace oot3d::recomp::a32;
static GuestState stateWith(std::uint64_t value) {
    GuestState state{};
    state.vfp[14] = static_cast<std::uint32_t>(value);
    state.vfp[15] = static_cast<std::uint32_t>(value >> 32);
    state.fpscr = 1U << 22; // Preserve rounding mode alongside comparison flags.
    return state;
}
int main() {
    for (auto raw : {0xEEB57B40U, 0xEEB57BC0U}) {
        assert(VfpBinary64Supported(raw));
        for (auto pair : {std::array<std::uint64_t, 2>{0x3ff0000000000000ULL, 0x20000000U},
                          std::array<std::uint64_t, 2>{0xbff0000000000000ULL, 0x80000000U},
                          std::array<std::uint64_t, 2>{0x8000000000000000ULL, 0x60000000U}}) {
            auto state = stateWith(pair[0]);
            auto result = ExecuteVfpBinary64(raw, 0x1000, state);
            assert(result.kind == ExitKind::Fallthrough && result.pc == 0x1004);
            assert((state.fpscr & 0xf0000000U) == pair[1]);
            assert((state.fpscr & (1U << 22)) != 0);
        }
    }
    auto quiet = stateWith(0x7ff8000000000000ULL);
    ExecuteVfpBinary64(0xEEB57B40U, 0x1000, quiet);
    assert((quiet.fpscr & 0xf0000001U) == 0x30000000U);
    auto signaling = stateWith(0x7ff8000000000000ULL);
    ExecuteVfpBinary64(0xEEB57BC0U, 0x1000, signaling);
    assert((signaling.fpscr & 0xf0000001U) == 0x30000001U);
    assert(!VfpBinary64Supported(0xEEB57BC1U));
    for (auto value : {0U, 1U, 0x80000000U, 0xffffffffU}) {
        GuestState state{};
        state.vfp[15] = value;
        assert(VfpBinary64Supported(0xEEB87B67U));
        auto result = ExecuteVfpBinary64(0xEEB87B67U, 0x1000, state);
        assert(result.kind == ExitKind::Fallthrough);
        const auto bits = std::uint64_t{state.vfp[14]} | (std::uint64_t{state.vfp[15]} << 32);
        assert(std::bit_cast<double>(bits) == static_cast<double>(value));
    }
}
