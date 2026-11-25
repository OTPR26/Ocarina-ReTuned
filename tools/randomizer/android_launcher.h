#pragma once
#if defined(__ANDROID__)
#include "native_launcher.h"
#include "android_session.h"
#include "android_preparation.h"
#include "launch_arguments.h"
#include "retuned_frontend_state.h"
#include <fstream>
#include <memory>

namespace RetunedRandomizer {
inline bool AndroidLaunch(const std::vector<std::string>& arguments,int slot,bool newGame) {
    return RetunedFrontend::StartupVisible &&
        AndroidSessions.Queue(arguments,slot,newGame);
}
struct AndroidLauncher {
    nlohmann::json config;
    NativeLauncher launcher;
    static nlohmann::json Read(const std::filesystem::path& path) {
        if(std::filesystem::is_symlink(path) || std::filesystem::file_size(path)>65536)
            throw std::runtime_error("Invalid randomizer runtime configuration");
        std::ifstream input(path);nlohmann::json config;input>>config;
        const std::filesystem::path data=config.at("app_data").get<std::string>();
        if(data.lexically_normal()!=path.parent_path()/"data" || std::filesystem::is_symlink(data))
            throw std::runtime_error("Invalid Android randomizer data directory");
        std::filesystem::create_directory(data);
        return config;
    }
    static PreparedRun Installed(const nlohmann::json& config) {
        if (!config.contains("installed_runtime") && config.value("device_preparation", false)) return {};
        const auto& runtime = config.at("installed_runtime");
        return {runtime.at("manifest").get<std::string>(), runtime.at("module").get<std::string>()};
    }
    AndroidLauncher(const std::filesystem::path& path):config(Read(path)),
      launcher(config.at("app_data").get<std::string>(),config.at("artifacts").get<std::string>(),
        Installed(config),
        RetunedFrontend::RandomizerMenu,[]{return RetunedFrontend::StartupVisible;},
        [this](const LaunchRequest& request) {
            if(!RetunedFrontend::StartupVisible)return false;
            return AndroidLaunch(LaunchArguments(config.at("app_data").get<std::string>(),
                config.at("normal_arguments").get<std::vector<std::string>>(),request),request.menuSlot,
                !std::filesystem::exists(request.run.profile/"native/save00.bin"));
        },
#if defined(RETUNED_RANDOMIZER_PRIVATE_TEST)
        true,
#else
        false,
#endif
        {},config.value("runtime_store", (path.parent_path() / "runtime-store").string()),
        config.value("device_preparation", false) ? RunLauncher::Prepare(
            [root = path.parent_path()](const auto& seed, const auto& progress) {
                return PrepareAndroidRun(root, seed, progress);
            }) : RunLauncher::Prepare{}) {
        auto& menu=RetunedFrontend::RandomizerMenu;
        if(const char* slot=std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) {
            menu.ActiveSlot=std::stoi(slot);
            menu.ActiveSeed=RunCatalog(config.at("app_data").get<std::string>()).Read(menu.ActiveSlot).seed;
            menu.SelectedAtStartup=true;RetunedFrontend::StartupVisible=false;
        } else if(std::getenv("RETUNED_RANDOMIZER_START_NORMAL"))RetunedFrontend::StartupVisible=false;
        menu.StartNormal=[this] {
            if(!RetunedFrontend::StartupVisible || menuBusy())return;
            if(!AndroidLaunch(config.at("normal_arguments").get<std::vector<std::string>>(),-1,false))
                RetunedFrontend::RandomizerMenu.Status="Could not restart the normal game.";
        };
    }
    static bool menuBusy(){auto& menu=RetunedFrontend::RandomizerMenu;return menu.Busy||menu.TransferBusy;}
};
inline std::unique_ptr<AndroidLauncher> AndroidHost;
inline void ResetAndroidLauncher() {
    AndroidHost.reset();
    RetunedFrontend::RandomizerMenu={};
}
inline void TickAndroidLauncher() {
    const char* path=std::getenv("RETUNED_RANDOMIZER_LAUNCHER");if(!path)return;
    auto& host=AndroidHost;
    static bool failed=false;
    if(failed)return;
    try {
        if(!host)host=std::make_unique<AndroidLauncher>(path);
        host->launcher.Poll();
    }catch(const std::exception& error){failed=true;RetunedFrontend::RandomizerMenu.Status=error.what();SDL_Log("Randomizer startup: %s",error.what());}
}
}
#endif
