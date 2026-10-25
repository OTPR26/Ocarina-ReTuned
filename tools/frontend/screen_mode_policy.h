// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "screen_presentation_bridge.h"
#include "screen_layout.h"
#include <cmath>
#include <cstdint>
#include <span>

namespace RetunedFrontend {
enum class ScreenPreference { Single, Dual, Hybrid };
enum class ScreenPlatform { Android, IPhoneDuo, Other };
struct ScreenCapabilities {
    ScreenPlatform Platform = ScreenPlatform::Other;
    bool PreparedGameSupportsSwitching = false;
    bool LowerViewAvailable = false;
};

inline bool ScreenPreferenceAllowed(ScreenPreference preference, ScreenPlatform platform) {
    if (preference == ScreenPreference::Single) return true;
    if (preference == ScreenPreference::Dual)
        return platform == ScreenPlatform::Android || platform == ScreenPlatform::IPhoneDuo;
    return preference == ScreenPreference::Hybrid && platform == ScreenPlatform::IPhoneDuo;
}

// This chooses a REQUEST, not the rendered layout. ScreenPresentationBridge
// commits the effective mode only after the prepared game acknowledges it.
// Preference belongs to the caller and is never overwritten by a fallback.
class ScreenModePolicy {
 public:
    GamePresentation Resolve(ScreenPreference preference, ScreenCapabilities capabilities,
                             bool laptopPostureConfirmed, uint64_t monotonicMilliseconds) {
        if (!ScreenPreferenceAllowed(preference, capabilities.Platform) ||
            !capabilities.PreparedGameSupportsSwitching || !capabilities.LowerViewAvailable ||
            preference == ScreenPreference::Single) {
            Reset();
            return GamePresentation::Single;
        }
        if (preference == ScreenPreference::Dual) {
            Reset();
            return GamePresentation::Dual;
        }
        // The platform must confirm posture from its real layout/orientation
        // and hinge information. A partial hinge angle alone is insufficient.
        if (mObserved && monotonicMilliseconds < mLastTime) Reset();
        if (!mObserved ||
            laptopPostureConfirmed != mCandidate) {
            mCandidate = laptopPostureConfirmed;
            mCandidateSince = monotonicMilliseconds;
            mObserved = true;
        }
        mLastTime = monotonicMilliseconds;
        if (monotonicMilliseconds - mCandidateSince >= 250)
            mLaptop = mCandidate;
        return mLaptop ? GamePresentation::Dual : GamePresentation::Single;
    }
 private:
    void Reset() { mObserved = mCandidate = mLaptop = false; mLastTime = mCandidateSince = 0; }
    bool mObserved = false, mCandidate = false, mLaptop = false;
    uint64_t mLastTime = 0, mCandidateSince = 0;
};

inline bool ValidScreenRect(ScreenRect r) {
    return std::isfinite(r.X) && std::isfinite(r.Y) && std::isfinite(r.Width) &&
           std::isfinite(r.Height) && r.Width > 0 && r.Height > 0 &&
           std::isfinite(r.X + r.Width) && std::isfinite(r.Y + r.Height);
}

// Coordinate space is the platform view's logical points, including its safe
// origin. A division strip comes from UIKit, not a guessed device midpoint.
inline GameScreenLayout LayoutDividedGameScreens(ScreenRect safe, ScreenRect division,
                                                GamePresentation mode) {
    if (!ValidScreenRect(safe)) return {};
    // Single uses the whole adaptive safe canvas; the scene projection follows
    // its aspect, instead of imposing a fixed phone-sized letterbox.
    if (mode == GamePresentation::Single) return {safe, {}};
    if (mode != GamePresentation::Dual || !ValidScreenRect(division)) return {};
    constexpr float epsilon = 0.5f;
    const float right = safe.X + safe.Width, bottom = safe.Y + safe.Height;
    if (division.X <= safe.X + epsilon && division.X + division.Width >= right - epsilon &&
        division.Y > safe.Y && division.Y + division.Height < bottom) {
        return {FitScreen({safe.X, safe.Y, safe.Width, division.Y - safe.Y}, 400.f/240.f),
                FitScreen({safe.X, division.Y + division.Height, safe.Width,
                           bottom - division.Y - division.Height}, 320.f/240.f)};
    }
    if (division.Y <= safe.Y + epsilon && division.Y + division.Height >= bottom - epsilon &&
        division.X > safe.X && division.X + division.Width < right) {
        return {FitScreen({safe.X, safe.Y, division.X - safe.X, safe.Height}, 400.f/240.f),
                FitScreen({division.X + division.Width, safe.Y,
                           right - division.X - division.Width, safe.Height}, 320.f/240.f)};
    }
    return {}; // An occlusion or ambiguous divider is not a second screen.
}
inline std::optional<LowerScreenTouch> MapUnoccludedLowerTouch(
        const GameScreenLayout& layout, float x, float y, std::span<const ScreenRect> occlusions) {
    for (const auto& region : occlusions)
        if (region.Contains(x, y)) return {};
    return MapLowerScreenTouch(layout, x, y);
}
}
