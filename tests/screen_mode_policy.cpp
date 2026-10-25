#include "screen_mode_policy.h"
#include <cassert>
#include <limits>
using namespace RetunedFrontend;
int main() {
    ScreenModePolicy policy;
    ScreenCapabilities duo{ScreenPlatform::IPhoneDuo, true, true};
    for (bool folded : {false, true}) {
        assert(policy.Resolve(ScreenPreference::Single, duo, folded, 0) == GamePresentation::Single);
        assert(policy.Resolve(ScreenPreference::Dual, duo, folded, 0) == GamePresentation::Dual);
    }
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, false, 1000) == GamePresentation::Single);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 2000) == GamePresentation::Single);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 2249) == GamePresentation::Single);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 2250) == GamePresentation::Dual);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, false, 2300) == GamePresentation::Dual);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 2400) == GamePresentation::Dual);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, false, 2600) == GamePresentation::Dual);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, false, 2850) == GamePresentation::Single);
    // Loss of a display/capability immediately requests Single, without
    // changing the saved preference or waiting through the posture debounce.
    auto absent = duo; absent.LowerViewAvailable = false;
    assert(policy.Resolve(ScreenPreference::Dual, absent, true, 3000) == GamePresentation::Single);
    assert(policy.Resolve(ScreenPreference::Dual, duo, false, 3001) == GamePresentation::Dual);
    absent = duo; absent.PreparedGameSupportsSwitching = false;
    assert(policy.Resolve(ScreenPreference::Dual, absent, true, 3002) == GamePresentation::Single);
    for (auto platform : {ScreenPlatform::Android, ScreenPlatform::Other}) {
        auto device = duo; device.Platform = platform;
        assert(!ScreenPreferenceAllowed(ScreenPreference::Hybrid, platform));
        assert(policy.Resolve(ScreenPreference::Hybrid, device, true, 4000) == GamePresentation::Single);
    }
    assert(!ScreenPreferenceAllowed(static_cast<ScreenPreference>(99), ScreenPlatform::IPhoneDuo));
    // A resetting monotonic clock must not underflow into an instant switch.
    policy.Resolve(ScreenPreference::Hybrid, duo, true, 9000);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 5) == GamePresentation::Single);
    assert(policy.Resolve(ScreenPreference::Hybrid, duo, true, 255) == GamePresentation::Dual);
    const ScreenRect safe{20, 40, 760, 960};
    auto single = LayoutDividedGameScreens(safe, {}, GamePresentation::Single);
    assert(single.Top.X == 20 && single.Top.Y == 40 && single.Top.Width == 760 && !single.Lower.Width);
    auto layout = LayoutDividedGameScreens(safe, {0, 500, 800, 20}, GamePresentation::Dual);
    assert(layout.Top.Y >= 40 && layout.Top.Y + layout.Top.Height <= 500);
    assert(layout.Lower.Y >= 520 && layout.Lower.Y + layout.Lower.Height <= 1000);
    assert(!MapLowerScreenTouch(layout, 400, 510));
    assert(!MapLowerScreenTouch(layout, 19, 800));
    auto touch = MapLowerScreenTouch(layout, layout.Lower.X + layout.Lower.Width/2,
                                    layout.Lower.Y + layout.Lower.Height/2);
    assert(touch && touch->X == 160 && touch->Y == 120);
    const ScreenRect camera{layout.Lower.X, layout.Lower.Y, 20, 20};
    assert(!MapUnoccludedLowerTouch(layout, camera.X+10, camera.Y+10, {&camera, 1}));
    assert(MapUnoccludedLowerTouch(layout, layout.Lower.X+layout.Lower.Width/2,
                                  layout.Lower.Y+layout.Lower.Height/2, {&camera, 1}));
    layout = LayoutDividedGameScreens(safe, {390, 0, 20, 1100}, GamePresentation::Dual);
    assert(layout.Top.X + layout.Top.Width <= 390 && layout.Lower.X >= 410);
    assert(!LayoutDividedGameScreens(safe, {100, 100, 10, 10}, GamePresentation::Dual).Lower.Width);
    assert(!LayoutDividedGameScreens(safe, {0, 40, 800, 20}, GamePresentation::Dual).Lower.Width);
    const float nan = std::numeric_limits<float>::quiet_NaN();
    assert(!LayoutDividedGameScreens({nan, 0, 800, 900}, {}, GamePresentation::Single).Top.Width);
}
