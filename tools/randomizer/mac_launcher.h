#pragma once
#include "desktop_documents.h"
#include "launch_arguments.h"
#include "native_launcher.h"
#include "retuned_frontend_state.h"
#include <cstdlib>
#include <fstream>
#include <memory>
#include <nlohmann/json.hpp>

namespace RetunedRandomizer {
class MacLauncher {
    NativeLauncher launcher_;
    DesktopDocuments documents_;
public:
    MacLauncher(const std::filesystem::path& runs, const PreparedRun& installed,
                const std::vector<std::string>& normal)
        : launcher_(runs, runs / "artifacts", installed, RetunedFrontend::RandomizerMenu,
            [] { return RetunedFrontend::StartupVisible; },
            [runs, normal](const LaunchRequest& request) {
                return RetunedFrontend::RequestGameLaunch &&
                    RetunedFrontend::RequestGameLaunch(LaunchArguments(runs, normal, request),
                        request.menuSlot, !std::filesystem::exists(request.run.profile / "native/save00.bin"));
            }, false, {}, runs / "runtime-store", {}, true),
          documents_(RetunedFrontend::RandomizerMenu, runs, [] { return RetunedFrontend::StartupVisible; }) {
        auto& menu = RetunedFrontend::RandomizerMenu;
        menu.StartNormal = [normal] {
            if (!RetunedFrontend::RequestGameLaunch || !RetunedFrontend::RequestGameLaunch(normal, -1, false))
                RetunedFrontend::RandomizerMenu.Status = "Could not open the normal game.";
        };
        if (const char* active = std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) {
            menu.ActiveSlot = std::stoi(active);
            menu.ActiveSeed = RunCatalog(runs).Read(menu.ActiveSlot).seed;
            menu.SelectedAtStartup = true;
            RetunedFrontend::StartupVisible = false;
        } else if (std::getenv("RETUNED_RANDOMIZER_START_NORMAL")) {
            RetunedFrontend::StartupVisible = false;
        }
    }
    void Poll() { launcher_.Poll(); }
};

inline void TickMacLauncher() {
    static std::unique_ptr<MacLauncher> host;
    static bool initialized = false;
    if (!initialized) {
        initialized = true;
        const char* profile = std::getenv("RETUNED_NORMAL_LAUNCH_PROFILE");
        if (!profile) return;
        try {
            const auto runs = std::filesystem::path(profile).parent_path() / "randomizer";
            const auto store = runs / "runtime-store";
            std::ifstream current(store / "active.json");
            if (!current) return;
            const auto id = nlohmann::json::parse(current).at("runtime").get<std::string>();
            if (id.size() != 64 || id.find_first_not_of("0123456789abcdef") != std::string::npos)
                throw std::runtime_error("Invalid installed Randomizer runtime");
            const auto path = store / "runtimes" / id;
            const auto normal = nlohmann::json::parse(std::ifstream(profile)).at("arguments").get<std::vector<std::string>>();
            host = std::make_unique<MacLauncher>(runs,
                PreparedRun{path / "process-manifest.json", path / "title.dylib"}, normal);
        } catch (const std::exception& error) {
            std::fprintf(stderr, "Randomizer setup: %s\n", error.what());
        }
    }
    if (host) host->Poll();
}
}
