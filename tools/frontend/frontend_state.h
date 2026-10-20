// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
namespace RetunedFrontend {
inline bool StartupVisible = true;
inline bool SetupVisible = false;
inline int RequestedSettingsPage = -1;
inline std::atomic<bool> NativeFrontendEnabled{false};
}
