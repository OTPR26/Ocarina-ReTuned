#include "oot3d_native_a32_clock.h"
#include <array>
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>

using namespace Oot3dNativeGame;

uint64_t Read64(const std::array<uint8_t, 4096>& page, size_t offset) {
    uint64_t value = 0;
    for (size_t i = 0; i < 8; ++i) value |= uint64_t(page[offset + i]) << (i * 8);
    return value;
}

int main() {
    std::tm time{};
    time.tm_year = 0;
    assert(ClockMillisecondsSince1900(time) == 0);
    time.tm_year = 100;
    assert(ClockMillisecondsSince1900(time) == 3155673600000ULL);
    time.tm_year = 124; // 2024-03-01, after a leap day
    time.tm_yday = 60;
    time.tm_hour = 12; time.tm_min = 34; time.tm_sec = 56;
    assert(ClockMillisecondsSince1900(time) == 3918285296000ULL);
    time.tm_year = -1;
    assert(!ClockMillisecondsSince1900(time));
    time.tm_year = 126; time.tm_hour = 24;
    assert(!ClockMillisecondsSince1900(time));

    std::array<uint8_t, 4096> page{};
    page[4] = 0x7B; page[0x66] = 0x5A;
    assert(InitializeSharedPageClock(page, 3918285296000ULL));
    for (size_t pos : {size_t{0x20}, size_t{0x40}}) {
        assert(Read64(page, pos) == 3918285296000ULL);
        assert(Read64(page, pos + 8) == 0);
        assert(Read64(page, pos + 16) == 268111856ULL);
        assert(Read64(page, pos + 24) == 0);
        // Guest clock formula should advance exactly one second after one
        // system-tick second.
        assert(Read64(page, pos) + 268111856ULL * 1000 / Read64(page, pos + 16)
               == 3918285297000ULL);
    }
    assert(page[4] == 0x7B && page[0x66] == 0x5A);
    std::array<uint8_t, 0x5f> tooShort{};
    assert(!InitializeSharedPageClock(tooShort, 1));

    // Clock publication must update only the inactive 32-byte reference and
    // publish its selector last. Advance wall time with the guest tick frozen
    // to represent Android suspension, then rewind the page and tick like a
    // save-state load; each new publication must use the real current time.
    std::vector<uint32_t> writes;
    const auto readCounter = [&](uint32_t* out) {
        *out = uint32_t(page[0]) | (uint32_t(page[1]) << 8) |
               (uint32_t(page[2]) << 16) | (uint32_t(page[3]) << 24);
        return true;
    };
    const auto write = [&](uint32_t offset, std::span<const uint8_t> data) {
        writes.push_back(offset);
        std::copy(data.begin(), data.end(), page.begin() + offset);
        return true;
    };
    assert(PublishSharedPageClock(readCounter, write, 3918285296000ULL, 9876));
    assert((writes == std::vector<uint32_t>{0x40, 0}));
    assert(page[0] == 1 && Read64(page, 0x40) == 3918285296000ULL &&
           Read64(page, 0x48) == 9876 && Read64(page, 0x50) == 268111856ULL &&
           Read64(page, 0x58) == 0 && Read64(page, 0x20) == 3918285296000ULL);
    auto savedPage = page;
    writes.clear();
    assert(PublishSharedPageClock(readCounter, write, 3918288896000ULL, 9876));
    assert((writes == std::vector<uint32_t>{0x20, 0}));
    assert(page[0] == 2 && Read64(page, 0x20) == 3918288896000ULL &&
           Read64(page, 0x28) == 9876);
    page = savedPage;
    writes.clear();
    assert(PublishSharedPageClock(readCounter, write, 3918292496000ULL, 9876));
    assert((writes == std::vector<uint32_t>{0x20, 0}));
    assert(page[0] == 2 && Read64(page, 0x20) == 3918292496000ULL);

    // An unreadable selector must not modify either reference or selector.
    const auto beforeReadFailure = page;
    const auto failingRead = [&](uint32_t*) { return false; };
    writes.clear();
    assert(!PublishSharedPageClock(failingRead, write, 1, 2));
    assert(writes.empty() && page == beforeReadFailure);

    // Failed reference writes must never switch the selector.
    const auto failingWrite = [&](uint32_t, std::span<const uint8_t>) { return false; };
    assert(!PublishSharedPageClock(readCounter, failingWrite, 1, 2));
    assert(page[0] == 2);
    const auto failCommit = [&](uint32_t offset, std::span<const uint8_t> data) {
        if (offset == 0) return false;
        return write(offset, data);
    };
    assert(!PublishSharedPageClock(readCounter, failCommit, 3, 4));
    assert(page[0] == 2 && Read64(page, 0x20) == 3918292496000ULL);
    // Unsigned counter wrap still selects the newly written reference.
    std::fill_n(page.begin(), 4, uint8_t{0xff});
    writes.clear();
    assert(PublishSharedPageClock(readCounter, write, 123, 456));
    assert((writes == std::vector<uint32_t>{0x20, 0}));
    assert(page[0] == 0 && page[1] == 0 && page[2] == 0 && page[3] == 0 &&
           Read64(page, 0x20) == 123 && Read64(page, 0x28) == 456);
    assert(HostLocalClockMillisecondsSince1900().has_value());
    std::puts("clock tests passed");
}
