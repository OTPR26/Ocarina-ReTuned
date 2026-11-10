#pragma once

#include <cstdint>
#include <cstddef>
#include <array>
#include <chrono>
#include <ctime>
#include <initializer_list>
#include <optional>
#include <span>

namespace Oot3dNativeGame {

// The 3DS clock is local console time, encoded as milliseconds since 1900.
// Convert civil fields directly rather than applying a historical host time-zone
// offset to 1900; that offset need not be the host's current offset.
inline std::optional<uint64_t> ClockMillisecondsSince1900(const std::tm& local) {
    const int64_t year = static_cast<int64_t>(local.tm_year) + 1900;
    if (year < 1900 || local.tm_yday < 0 || local.tm_yday > 365 ||
        local.tm_hour < 0 || local.tm_hour > 23 || local.tm_min < 0 ||
        local.tm_min > 59 || local.tm_sec < 0 || local.tm_sec > 60) {
        return std::nullopt;
    }
    const auto leapDaysThrough = [](int64_t y) {
        return y / 4 - y / 100 + y / 400;
    };
    const int64_t days = (year - 1900) * 365 +
        leapDaysThrough(year - 1) - leapDaysThrough(1899) + local.tm_yday;
    const int64_t seconds = ((days * 24 + local.tm_hour) * 60 + local.tm_min) * 60 + local.tm_sec;
    return static_cast<uint64_t>(seconds) * 1000;
}

inline std::optional<uint64_t> HostLocalClockMillisecondsSince1900() {
    const auto now = std::chrono::system_clock::now();
    const auto wholeSeconds = std::chrono::floor<std::chrono::seconds>(now);
    const auto fractionalMs = std::chrono::duration_cast<std::chrono::milliseconds>(now - wholeSeconds).count();
    const std::time_t timestamp = std::chrono::system_clock::to_time_t(wholeSeconds);
    if (timestamp == static_cast<std::time_t>(-1)) return std::nullopt;
    std::tm local{};
#if defined(_WIN32)
    if (localtime_s(&local, &timestamp) != 0) return std::nullopt;
#else
    if (localtime_r(&timestamp, &local) == nullptr) return std::nullopt;
#endif
    const auto base = ClockMillisecondsSince1900(local);
    return base ? std::optional<uint64_t>(*base + static_cast<uint64_t>(fractionalMs)) : std::nullopt;
}

// Initial CTR system tick is zero; the guest interpolates elapsed time from
// the tick count and 268111856 Hz between reference point refreshes.
inline bool InitializeSharedPageClock(std::span<uint8_t> bytes, uint64_t localMs) {
    if (bytes.size() < 0x60U) return false;
    const auto write64 = [&](size_t offset, uint64_t value) {
        for (size_t index = 0; index < 8; ++index)
            bytes[offset + index] = static_cast<uint8_t>(value >> (index * 8));
    };
    for (const size_t offset : {size_t{0x20}, size_t{0x40}}) {
        write64(offset, localMs);
        write64(offset + 8, 0);
        write64(offset + 16, 268111856ULL);
        write64(offset + 24, 0);
    }
    return true;
}

// Called only while the guest is stopped at a refresh boundary. The inactive
// time reference is written in full before the counter selects it. The 3DS
// osGetTimeRef protocol retries if this counter changes during its read.
// Callbacks keep this routine testable without a guest memory implementation.
template <typename ReadCounter, typename WriteBytes>
bool PublishSharedPageClock(ReadCounter readCounter, WriteBytes writeBytes,
                            uint64_t localMs, uint64_t systemTicks) {
    uint32_t counter = 0;
    if (!readCounter(&counter)) return false;
    std::array<uint8_t, 32> reference{};
    const auto put = [&](size_t offset, uint64_t value) {
        for (size_t index = 0; index < 8; ++index)
            reference[offset + index] = static_cast<uint8_t>(value >> (index * 8));
    };
    put(0, localMs);
    put(8, systemTicks);
    put(16, 268111856ULL);
    put(24, 0);
    const uint32_t inactiveOffset = (counter & 1U) ? 0x20U : 0x40U;
    if (!writeBytes(inactiveOffset, std::span<const uint8_t>(reference))) return false;
    const uint32_t next = counter + 1U;
    const std::array<uint8_t, 4> selector{
        static_cast<uint8_t>(next), static_cast<uint8_t>(next >> 8),
        static_cast<uint8_t>(next >> 16), static_cast<uint8_t>(next >> 24)};
    return writeBytes(0, std::span<const uint8_t>(selector));
}

} // namespace Oot3dNativeGame
