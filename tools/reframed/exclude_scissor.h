#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace Retuned {
struct ScissorRect { int32_t X, Y; uint32_t Width, Height; };
struct ScissorParts { std::array<ScissorRect, 4> Rects{}; uint32_t Count = 0; };

// Partition the visible region into disjoint rectangles, so blending and stencil
// operations still execute exactly once for every retained fragment.
inline ScissorParts ExcludeScissor(ScissorRect bounds, ScissorRect hole) {
    ScissorParts result;
    const int64_t left = bounds.X, top = bounds.Y;
    const int64_t right = left + bounds.Width, bottom = top + bounds.Height;
    const int64_t x1 = std::clamp<int64_t>(hole.X, left, right);
    const int64_t y1 = std::clamp<int64_t>(hole.Y, top, bottom);
    const int64_t x2 = std::clamp<int64_t>(int64_t{hole.X} + hole.Width, left, right);
    const int64_t y2 = std::clamp<int64_t>(int64_t{hole.Y} + hole.Height, top, bottom);
    auto add = [&](int64_t x, int64_t y, int64_t r, int64_t b) {
        if (r > x && b > y) result.Rects[result.Count++] = {
            static_cast<int32_t>(x), static_cast<int32_t>(y),
            static_cast<uint32_t>(r-x), static_cast<uint32_t>(b-y)};
    };
    if (x2 <= x1 || y2 <= y1) { add(left, top, right, bottom); return result; }
    add(left, top, right, y1);
    add(left, y2, right, bottom);
    add(left, y1, x1, y2);
    add(x2, y1, right, y2);
    return result;
}
}
