#include "../tools/frontend/render_resolution.h"
#include <cassert>
#include <limits>
int main() {
    using namespace RetunedFrontend;
    const auto scale = GameplayScaleForHeight(720, 2160);
    auto extent = GameplayResolution(3840, 2160, scale);
    assert(extent.Width == 1280 && extent.Height == 720);
    extent = GameplayResolution(3840, 2160, .5f);
    assert(extent.Width == 1920 && extent.Height == 1080);
    extent = GameplayResolution(3840, 2160, 1.f);
    assert(extent.Width == 3840 && extent.Height == 2160);
    extent = GameplayResolution(1920, 1080, GameplayScaleForHeight(720, 1080));
    assert(extent.Width == 1280 && extent.Height == 720);
    extent = GameplayResolution(2560, 1600, GameplayScaleForHeight(720, 1600));
    assert(extent.Width == 1152 && extent.Height == 720);
    assert(GameplayScale(0.f) == MinimumRenderScale);
    assert(GameplayScale(3.f) == 2.f);
    assert(GameplayScale(std::numeric_limits<float>::quiet_NaN()) == 1.f);
}
