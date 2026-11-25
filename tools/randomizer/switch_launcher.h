#pragma once
#include "native_launcher.h"
#include "launch_arguments.h"
#include "retuned_frontend_state.h"
#include "../native/setup/game_handoff.h"
#include <fstream>
#include <memory>

extern "C" const char retuned_switch_randomizer_id[] __attribute__((weak));
namespace RetunedRandomizer {
inline RetunedSetup::GameHandoff SwitchHandoff;
inline std::unique_ptr<NativeLauncher> SwitchLauncher;
inline const std::filesystem::path SwitchData = "/switch/oot3dre/randomizer";
inline std::vector<std::string> SwitchNormalArgs;
inline bool SwitchChecked = false;

inline void TickSwitchLauncher() {
    auto& menu = RetunedFrontend::RandomizerMenu;
    if (!SwitchChecked) {
        SwitchChecked = true;
        if (!retuned_switch_randomizer_id || SwitchNormalArgs.empty()) return;
        const auto runtime = SwitchData / "runtime";
        const auto marker = runtime / "title.id";
        std::string id;
        if (!(std::ifstream(marker) >> id) || id != retuned_switch_randomizer_id) {
            std::fprintf(stderr, "Randomizer SD data does not match the installed title\n");
            return;
        }
        SwitchLauncher = std::make_unique<NativeLauncher>(SwitchData, SwitchData / "artifacts",
            PreparedRun{runtime / "process-manifest.json", marker}, menu,
            [] { return RetunedFrontend::StartupVisible; },
            [](const LaunchRequest& request) {
                auto arguments = SwitchNormalArgs;
                arguments.insert(arguments.end(), {"--title-plugin", "static"});
                arguments = LaunchArguments(SwitchData, std::move(arguments), request);
                return SwitchHandoff.Queue({std::move(arguments), static_cast<int>(request.menuSlot),
                    !std::filesystem::exists(request.run.profile / "native/save00.bin")});
            });
        menu.StartNormal = [] { SwitchHandoff.Queue({SwitchNormalArgs, -1, false}); };
    }
    if (SwitchLauncher) SwitchLauncher->Poll();
}
}
