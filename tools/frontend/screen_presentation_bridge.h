// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <optional>

namespace RetunedFrontend {
enum class GamePresentation : uint32_t { Single = 0, Dual = 1 };

// Frame-boundary handshake. Rendering must follow the guest's acknowledged
// state, never a pending selection. The caller retries deferred requests.
class ScreenPresentationBridge {
 public:
    void Bind(uint32_t schema, uint32_t getMode, uint32_t trySetMode) {
        mGet = mSet = 0;
        mFaulted = false;
        mEffective = GamePresentation::Single;
        if (schema == 1 && getMode && trySetMode && getMode != trySetMode &&
            getMode % 4 == 0 && trySetMode % 4 == 0) {
            mGet = getMode;
            mSet = trySetMode;
        }
    }
    bool Supported() const { return mGet && mSet; }
    bool Faulted() const { return mFaulted; }
    GamePresentation Effective() const { return mEffective; }
    // Invoke returns no value on an execution failure. It must validate the
    // executable address against the current prepared module.
    template<class Invoke>
    bool Update(GamePresentation requested, Invoke invoke) {
        if (!Supported() || mFaulted) return false;
        if (requested != GamePresentation::Single && requested != GamePresentation::Dual)
            return false;
        const auto current = invoke(mGet, std::optional<uint32_t>{});
        if (!current || *current > 1) { mFaulted = true; return false; }
        mEffective = static_cast<GamePresentation>(*current);
        if (requested == mEffective) return true;
        const auto accepted = invoke(mSet, uint32_t(requested));
        if (!accepted || *accepted > 1) { mFaulted = true; return false; }
        if (!*accepted) return false;
        const auto settled = invoke(mGet, std::optional<uint32_t>{});
        if (!settled || *settled > 1 || *settled != uint32_t(requested)) {
            mFaulted = true;
            return false;
        }
        mEffective = static_cast<GamePresentation>(*settled);
        return mEffective == requested;
    }
 private:
    uint32_t mGet = 0, mSet = 0;
    bool mFaulted = false;
    GamePresentation mEffective = GamePresentation::Single;
};
}
