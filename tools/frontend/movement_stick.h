// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace RetunedFrontend {
inline std::array<std::int16_t, 2> MapMovementStick(
    std::int16_t rawX, std::int16_t rawY, int deadZonePercent, int nativeMaximum) {
    const double x = std::clamp(int(rawX), -32767, 32767) / 32767.0;
    const double y = std::clamp(int(rawY), -32767, 32767) / 32767.0;
    const double magnitude = std::hypot(x, y);
    const double deadZone = std::clamp(deadZonePercent, 0, 99) / 100.0;
    if (magnitude <= deadZone || magnitude == 0) return {0, 0};
    const double output = (std::min(magnitude, 1.0) - deadZone) / (1.0 - deadZone);
    const double scale = output * nativeMaximum / magnitude;
    return {static_cast<std::int16_t>(std::lround(x * scale)),
            static_cast<std::int16_t>(std::lround(y * scale))};
}
}
