#include "../tools/frontend/render_resolution.h"
#include "../tools/native/apple/television_resolution.h"
#include <cassert>
#include <limits>
#include <string>
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
    assert(RetunedTV::UseDefaultResolution(false, false, 0.0));
    assert(RetunedTV::UseDefaultResolution(false, true, 1.0));
    assert(!RetunedTV::UseDefaultResolution(false, true, .5));
    assert(!RetunedTV::UseDefaultResolution(false, true, 1.0 / 3.0));
    assert(!RetunedTV::UseDefaultResolution(true, true, 1.0));
#if !defined(_WIN32)
    unsetenv("RETUNED_DEFAULT_RENDER_SCALE");
    assert(DefaultGameplayScale() == 1.f);
    for (const auto height : {720U, 1080U, 2160U}) {
        const auto value = std::to_string(GameplayScaleForHeight(720, height));
        setenv("RETUNED_DEFAULT_RENDER_SCALE", value.c_str(), 1);
        assert(GameplayResolution(height * 16 / 9, height, DefaultGameplayScale()).Height == 720);
    }
    setenv("RETUNED_DEFAULT_RENDER_SCALE", "invalid", 1);
    assert(DefaultGameplayScale() == 1.f);
    unsetenv("RETUNED_DEFAULT_RENDER_SCALE");
#endif
}
