// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_screen_presentation_bridge.h"
#include "fast/oot3d/retuned_screen_probe.h"
#include "oot3d_native_a32_process.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <span>
#include <array>
#include <string>
#include <stdexcept>

namespace RetunedFrontend {
class ReframedScreenProbe {
 public:
    void Initialize(const std::filesystem::path& manifest) {
        if (!ScreenProbeRequested()) return;
        std::ifstream file(manifest);
        nlohmann::json root;
        file >> root;
        if (!root.contains("reframed_frontend") || !root.at("reframed_frontend").contains("presentation")) return;
        const auto& bridge = root.at("reframed_frontend").at("presentation");
        if (bridge.at("modes") != nlohmann::json::array({"single", "dual"}))
            throw std::runtime_error("Unsupported ReFramed presentation modes");
        const auto& functions = bridge.at("functions");
        mBridge.Bind(bridge.at("schema"), functions.at("ScreenPresentation_GetMode"),
                     functions.at("ScreenPresentation_TrySetMode"));
        if (!mBridge.Supported())
            throw std::runtime_error("Unsupported prepared-game presentation capability");
        ProbeGuestBridgeBound = true;
    }
    bool Apply(Oot3dNativeGame::NativeA32Process& process, uint64_t frame) {
        if (!mBridge.Supported()) return false;
        GamePresentation requested = DuoProbeRequested() ? DuoDisplay.Requested(mBridge.Supported()) : GamePresentation::Dual;
        // Private diagnostic control only. No saved user preference is changed.
        if (const char* path = std::getenv("RETUNED_SCREEN_PROBE_CONTROL")) {
            std::ifstream control(path);
            std::string value;
            control >> value;
            if (value == "single") requested = GamePresentation::Single;
            else if (value != "dual") return false;
        }
        const auto previous = mBridge.Effective();
        mBridge.Update(requested, [&](uint32_t entry, std::optional<uint32_t> argument)
                -> std::optional<uint32_t> {
            auto& memory = process.Memory();
            uint32_t result = 0;
            std::string error;
            const auto args = argument ? std::span<const uint32_t>(&*argument, 1)
                                       : std::span<const uint32_t>{};
            if (!memory.IsExecutable(entry, 4) ||
                !process.InvokeFunctionWithResult(entry, args, 0xFFFF0000U, &result, &error))
                return {};
            return result;
        });
        if (mBridge.Faulted())
            throw std::runtime_error("Screen-presentation handshake failed; stopping the isolated probe");
        ProbeGuestDualActive = mBridge.Effective() == GamePresentation::Dual;
        bool layoutChanged = false;
        if (DuoProbeRequested()) {
            const auto layout = DuoDisplay.Layout(1,1,ProbeGuestDualActive.load());
            const std::array<float,8> values{layout.Top.X,layout.Top.Y,layout.Top.Width,layout.Top.Height,
                layout.Lower.X,layout.Lower.Y,layout.Lower.Width,layout.Lower.Height};
            layoutChanged = !mLastLayout || *mLastLayout != values;
            mLastLayout = values;
        }
        if (previous == mBridge.Effective()) return layoutChanged;
        std::cout << "RETUNED_SCREEN_SWITCH frame=" << frame << " mode="
                  << (ProbeGuestDualActive ? "dual" : "single") << std::endl;
        return true;
    }
 private:
    ScreenPresentationBridge mBridge;
    std::optional<std::array<float,8>> mLastLayout;
};
inline ReframedScreenProbe NativeScreenProbe;
}
