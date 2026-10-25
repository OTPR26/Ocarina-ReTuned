// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
namespace RetunedFrontend {
// The saved preference and the session-only visibility toggle are separate.
struct TouchVisibilityState {
    std::atomic<bool> Configured;
    std::atomic<bool> Hidden{false};
    explicit TouchVisibilityState(bool enabled) : Configured(enabled) {}
    void Configure(bool enabled) { Hidden=false;Configured=enabled; }
    void Show(bool visible) { Hidden=Configured.load() && !visible; }
    bool ControlsVisible() const { return Configured.load() && !Hidden.load(); }
    bool ButtonVisible() const { return Configured.load(); }
};
}
