// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <optional>
namespace RetunedFrontend {
struct AndroidLowerExtent { uint32_t Width, Height; };
inline std::optional<AndroidLowerExtent> AndroidLowerRenderExtent(
    uint32_t guestWidth, uint32_t guestHeight, uint32_t surfaceWidth, uint32_t surfaceHeight) {
    // Native lower targets are rotated 240x320, or 480x320 with two
    // horizontal samples per displayed pixel. Preserve that transfer ratio.
    if ((guestWidth != 240 && guestWidth != 480) || guestHeight != 320 ||
        !surfaceWidth || !surfaceHeight) return {};
    const float width=std::min(float(surfaceWidth),float(surfaceHeight)*4.f/3.f);
    const auto outputWidth=std::max(1u,uint32_t(std::lround(width)));
    const auto outputHeight=std::max(1u,uint32_t(std::lround(width*3.f/4.f)));
    return AndroidLowerExtent{outputHeight*(guestWidth/240),outputWidth};
}
}
