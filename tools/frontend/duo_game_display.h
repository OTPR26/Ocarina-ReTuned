// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "screen_mode_policy.h"
#include "lower_equipment_state.h"
#include <mutex>
#include <vector>
#include <utility>

namespace RetunedFrontend {
struct DuoDisplayGeometry {
    bool Available = false;
    bool Closed = true;
    ScreenRect Bounds, Safe, Division;
    std::vector<ScreenRect> Occlusions;
};
// UIKit publishes logical view coordinates; rendering and SDL input request
// layouts in their own units. Keep both derived from the same geometry.
class DuoGameDisplay {
 public:
    void Publish(DuoDisplayGeometry geometry) {
        std::lock_guard lock(mMutex);
        mGeometry = std::move(geometry);
    }
    void Select(ScreenPreference preference) {
        std::lock_guard lock(mMutex);
        // Hybrid is deliberately unavailable until posture is validated.
        if (preference == ScreenPreference::Single || preference == ScreenPreference::Dual)
            mPreference = preference;
    }
    bool Available() const {
        std::lock_guard lock(mMutex);
        return mGeometry.Available;
    }
    ScreenPreference Preference() const {
        std::lock_guard lock(mMutex);
        return mPreference;
    }
    ScreenRect LowerPanelBounds(float width,float height,bool guestDual) const {
        std::lock_guard lock(mMutex);
        if (!guestDual || !CanShowLower() || !ValidScreenRect(mGeometry.Bounds)) return {};
        return Scale(LowerPane(),width/mGeometry.Bounds.Width,height/mGeometry.Bounds.Height);
    }
    GamePresentation Requested(bool compatible) {
        std::lock_guard lock(mMutex);
        return mPolicy.Resolve(mPreference, {ScreenPlatform::IPhoneDuo, compatible,
            CanShowLower()}, false, 0);
    }
    GameScreenLayout Layout(float width, float height, bool guestDual) const {
        std::lock_guard lock(mMutex);
        return LayoutLocked(width, height, guestDual);
    }
    std::optional<LowerScreenTouch> Touch(float width, float height, bool guestDual,
                                        float x, float y) const {
        std::lock_guard lock(mMutex);
        if (!CanShowLower() || !guestDual || !ValidScreenRect(mGeometry.Bounds)) return {};
        const float sx = width / mGeometry.Bounds.Width, sy = height / mGeometry.Bounds.Height;
        for (const auto& r : mGeometry.Occlusions)
            if (Scale(r, sx, sy).Contains(x,y)) return {};
        return MapLowerScreenTouch(LayoutLocked(width,height,guestDual),x,y);
    }
 private:
    ScreenRect LowerPane() const {
        const auto s=mGeometry.Safe,d=mGeometry.Division;
        if (d.Width>=s.Width-.5f)
            return {s.X,d.Y+d.Height,s.Width,s.Y+s.Height-d.Y-d.Height};
        return {d.X+d.Width,s.Y,s.X+s.Width-d.X-d.Width,s.Height};
    }
    bool CanShowLower() const {
        if (!mGeometry.Available || mGeometry.Closed) return false;
        const auto layout = LayoutDividedGameScreens(mGeometry.Safe, mGeometry.Division,
                                                     GamePresentation::Dual);
        return layout.Top.Width > 0 && layout.Lower.Width > 0;
    }
    ScreenRect Scale(ScreenRect r,float sx,float sy) const {
        return {(r.X-mGeometry.Bounds.X)*sx,(r.Y-mGeometry.Bounds.Y)*sy,r.Width*sx,r.Height*sy};
    }
    GameScreenLayout LayoutLocked(float width,float height,bool guestDual) const {
        if (!ValidScreenRect(mGeometry.Bounds) || !std::isfinite(width) ||
            !std::isfinite(height) || width<=0 || height<=0) return {};
        const auto mode = guestDual && CanShowLower() ? GamePresentation::Dual : GamePresentation::Single;
        auto layout = LayoutDividedGameScreens(mGeometry.Safe,mGeometry.Division,mode);
        if (mode==GamePresentation::Dual && LowerEquipmentPanelEnabled.load())
            layout.Lower.Y=LowerPane().Y;
        const float sx=width/mGeometry.Bounds.Width, sy=height/mGeometry.Bounds.Height;
        layout.Top=Scale(layout.Top,sx,sy);
        if (layout.Lower.Width>0) layout.Lower=Scale(layout.Lower,sx,sy);
        return layout;
    }
    mutable std::mutex mMutex;
    DuoDisplayGeometry mGeometry;
    ScreenPreference mPreference=ScreenPreference::Single;
    ScreenModePolicy mPolicy;
};
inline DuoGameDisplay DuoDisplay;
}
