// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cmath>
namespace RetunedTV {
inline bool UseDefaultResolution(bool initialized, bool hasScale, double scale) {
    return !hasScale || (!initialized && std::abs(scale - 1.0) < .000001);
}
}
