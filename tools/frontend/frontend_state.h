// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <string>
#include <functional>
#include <vector>
#include "retuned_settings_pages.h"
#include "retuned_randomizer_model.h"
namespace RetunedFrontend {
inline std::function<void()> RequestGamePreparation;
inline std::function<void()> RequestPortableMode;
inline bool PortableModeActive=false;
inline std::function<void()> RequestPlayerModels;
inline std::function<bool(std::vector<std::string>, int, bool)> RequestGameLaunch;
inline bool StartupVisible = true;
inline bool SetupVisible = false;
inline bool GameFilesReady = false;
inline int RequestedSettingsPage = -1;
inline std::atomic<bool> NativeFrontendEnabled{false};
inline bool DialogueFontChoicesAvailable = false;
inline std::string ActiveDialogueFontWeight = "bold";
}
