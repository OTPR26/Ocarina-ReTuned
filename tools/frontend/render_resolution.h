// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace RetunedFrontend {
inline constexpr float MinimumRenderScale = 1.f / 3.f;
struct GameplayExtent { uint32_t Width, Height; };
inline float GameplayScale(float scale) {
    return std::isfinite(scale) ? std::clamp(scale, MinimumRenderScale, 2.f) : 1.f;
}
inline GameplayExtent GameplayResolution(uint32_t width, uint32_t height, float scale) {
    scale = GameplayScale(scale);
    return {std::max(1U, uint32_t(std::lround(width * scale))),
            std::max(1U, uint32_t(std::lround(height * scale)))};
}
inline float GameplayScaleForHeight(uint32_t height, uint32_t outputHeight) {
    return outputHeight ? GameplayScale(float(height) / outputHeight) : 1.f;
}
}
