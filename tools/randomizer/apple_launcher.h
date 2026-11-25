#pragma once
#include "native_launcher.h"
#include "android_session.h"
#include "launch_arguments.h"
#include "retuned_frontend_state.h"
#include <cstdlib>
#include <fstream>
#include <memory>
#include <nlohmann/json.hpp>

namespace RetunedRandomizer {
inline AndroidSessionQueue AppleSessions;
inline std::unique_ptr<NativeLauncher> AppleHost;

inline void TickAppleLauncher() {
    if (!AppleHost) {
        const char* data = std::getenv("RETUNED_DATA_DIRECTORY");
        if (!data || !RetunedFrontend::StartupVisible || std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) return;
        const auto root = std::filesystem::path(data);
        nlohmann::json profile;
        std::ifstream(root / "native-launch.json") >> profile;
        auto arguments = profile.at("arguments").get<std::vector<std::string>>();
        const auto title = std::find(arguments.begin(), arguments.end(), "--title-plugin");
        if (title == arguments.end() || std::next(title) == arguments.end())
            throw std::runtime_error("The private Randomizer test framework is missing");
        const auto runs = root / "randomizer";
        const auto normalModule = std::filesystem::path(*std::next(title));
        const auto frameworks = normalModule.parent_path().parent_path();
        const auto resources = frameworks.parent_path() / "PrivateGame";
        const bool combined = std::filesystem::is_directory(resources / "Randomizer");
        if (!combined && !std::filesystem::is_regular_file(resources / "seed.json")) return;
        const auto module = combined ? frameworks / "retuned_randomizer.framework/retuned_randomizer" : normalModule;
        const auto manifest = (combined ? runs / "installed" : root) / "process-manifest.json";
        // Install updates relocate the app bundle and invalidate old absolute paths.
        const auto install = module.parent_path().parent_path().parent_path().parent_path().filename();
        std::filesystem::create_directories(runs);
        const auto* testHost = std::getenv("RETUNED_APPLE_TEST_HOST");
        const bool development = testHost && std::string_view(testHost) == "1";
        AppleHost = std::make_unique<NativeLauncher>(
            runs, runs / "artifacts" / install, PreparedRun{manifest, module},
            RetunedFrontend::RandomizerMenu, [] { return RetunedFrontend::StartupVisible; },
            [runs, arguments](const LaunchRequest& request) {
                return AppleSessions.Queue(LaunchArguments(runs, arguments, request), request.menuSlot,
                    !std::filesystem::exists(request.run.profile / "native/save00.bin"));
            }, development, std::vector<std::filesystem::path>{}, std::filesystem::path{},
            RunLauncher::Prepare{}, true);
        RetunedFrontend::RandomizerMenu.SelectedAtStartup = !combined;
    }
    AppleHost->Poll();
}
}
