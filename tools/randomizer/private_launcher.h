#pragma once
// Private macOS integration only; never staged into release packages.
#include "menu_binding.h"
#include "native_launcher.h"
#include "launch_arguments.h"
#include "desktop_documents.h"
#include "retuned_frontend_state.h"
#include <nlohmann/json.hpp>
#include <SDL.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <poll.h>
#include <fstream>
#include <random>
extern char **environ;
namespace RetunedRandomizer {
namespace Private {
using Json=nlohmann::json;
inline Json Read(const std::filesystem::path& path) {
    std::ifstream input(path); input.exceptions(std::ios::badbit|std::ios::failbit);
    Json value; input>>value; return value;
}
inline std::string Text(const std::filesystem::path& path) {
    std::ifstream input(path); input.exceptions(std::ios::badbit);
    return {std::istreambuf_iterator<char>(input), {}};
}
inline void Write(const std::filesystem::path& path,const Json& value) {
    const auto partial=path.string()+".partial";
    {std::ofstream out(partial);out.exceptions(std::ios::badbit|std::ios::failbit);out<<value.dump(2);out.close();}
    std::filesystem::rename(partial,path);
}
inline std::string Nonce() {
    std::random_device random;
    return std::to_string(random())+std::to_string(random());
}
inline std::vector<std::filesystem::path> RetainedModules(const Json& config) {
    std::vector<std::filesystem::path> modules;
    for(const auto& path:config.value("retained_modules",std::vector<std::string>{}))
        modules.emplace_back(path);
    return modules;
}
inline void Run(std::vector<std::string> arguments,const RunLauncher::Progress& progress) {
    int pipefd[2]; if(pipe(pipefd))throw std::runtime_error("Could not open preparation pipe");
    posix_spawn_file_actions_t actions;posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_adddup2(&actions,pipefd[1],STDOUT_FILENO);
    posix_spawn_file_actions_adddup2(&actions,pipefd[1],STDERR_FILENO);
    posix_spawn_file_actions_addclose(&actions,pipefd[0]);
    posix_spawn_file_actions_addclose(&actions,pipefd[1]);
    posix_spawnattr_t attributes;posix_spawnattr_init(&attributes);
    posix_spawnattr_setflags(&attributes,POSIX_SPAWN_SETPGROUP);
    posix_spawnattr_setpgroup(&attributes,0);
    std::vector<char*> argv;for(auto& s:arguments)argv.push_back(s.data());argv.push_back(nullptr);
    pid_t pid=0;const int error=posix_spawn(&pid,argv[0],&actions,&attributes,argv.data(),environ);
    posix_spawn_file_actions_destroy(&actions);posix_spawnattr_destroy(&attributes);close(pipefd[1]);
    if(error){close(pipefd[0]);throw std::runtime_error("Could not start preparation tool");}
    try {
        std::string pending, last="Working…";
        for (;;) {
            pollfd descriptor{pipefd[0],POLLIN,0};
            int ready=poll(&descriptor,1,250);
            if(ready<0&&errno==EINTR)continue;
            if(ready<0)throw std::runtime_error("Could not read preparation progress");
            progress(last); // Also checks cancellation while the compiler is quiet.
            if(!ready)continue;
            char bytes[1024];auto count=read(pipefd[0],bytes,sizeof(bytes));
            if(count==0)break;
            if(count<0&&errno==EINTR)continue;
            if(count<0)throw std::runtime_error("Could not read preparation output");
            pending.append(bytes,count);
            for(auto end=pending.find('\n');end!=std::string::npos;end=pending.find('\n')) {
                const auto line=pending.substr(0,end);pending.erase(0,end+1);
                for(const char* stage:{"Composing game","Translating game","Generating native module",
                                      "Configuring native module","Building native module"})
                    if(line==stage)last=line;
            }
            if(pending.size()>4096)pending.clear();
        }
        close(pipefd[0]);pipefd[0]=-1;
        int status=0;pid_t waited;do{waited=waitpid(pid,&status,0);}while(waited<0&&errno==EINTR);
        if(waited!=pid||!WIFEXITED(status)||WEXITSTATUS(status))throw std::runtime_error("Game preparation failed; see the private build log");
    }catch(...){if(pipefd[0]>=0)close(pipefd[0]);kill(-pid,SIGTERM);waitpid(pid,nullptr,0);throw;}

}
struct NativeHost {
    Json config;
    NativeLauncher launcher;
    DesktopDocuments documents;
    NativeHost(const std::filesystem::path& path):config(Read(path)),
      launcher(config.at("app_data").get<std::string>(),config.at("artifacts").get<std::string>(),
        {config.at("installed_runtime").at("manifest").get<std::string>(),
         config.at("installed_runtime").at("module").get<std::string>()},
        RetunedFrontend::RandomizerMenu,[]{return RetunedFrontend::StartupVisible;},
        [this](const LaunchRequest& request) {
            if(config.value("native_handoff",false)) {
                const auto arguments=LaunchArguments(config.at("app_data").get<std::string>(),
                    config.at("normal_arguments").get<std::vector<std::string>>(),request);
                return RetunedFrontend::RequestGameLaunch && RetunedFrontend::RequestGameLaunch(
                    arguments,request.menuSlot,!std::filesystem::exists(request.run.profile/"native/save00.bin"));
            }
            Write(config.at("handoff").get<std::string>(),Json{{"mode","randomizer"},
                {"manifest",request.prepared.manifest.string()},{"module",request.prepared.module.string()},
                {"profile",request.run.profile.string()},{"slot",request.menuSlot},{"seed",request.run.seed}});
            SDL_Event event{};event.type=SDL_QUIT;return SDL_PushEvent(&event)==1;
        },true,RetainedModules(config),config.value("runtime_store",std::string{})),documents(RetunedFrontend::RandomizerMenu,config.at("app_data").get<std::string>(),
            []{return RetunedFrontend::StartupVisible;}) {
        auto& menu=RetunedFrontend::RandomizerMenu;
        menu.StartNormal=[this] {
            if(config.value("native_handoff",false)) {
                if(!RetunedFrontend::RequestGameLaunch || !RetunedFrontend::RequestGameLaunch(
                    config.at("normal_arguments").get<std::vector<std::string>>(),-1,false))
                    RetunedFrontend::RandomizerMenu.Status="Could not return to the normal game";
                return;
            }
            Write(config.at("handoff").get<std::string>(),Json{{"mode","normal"}});
            SDL_Event event{};event.type=SDL_QUIT;SDL_PushEvent(&event);
        };
        if(const char* slot=getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) {
            menu.ActiveSlot=std::stoi(slot);
            menu.ActiveSeed=RunCatalog(config.at("app_data").get<std::string>()).Read(menu.ActiveSlot).seed;
            menu.SelectedAtStartup=true;RetunedFrontend::StartupVisible=false;
        } else if(getenv("RETUNED_RANDOMIZER_START_NORMAL"))RetunedFrontend::StartupVisible=false;
    }
};
struct Host {
    std::filesystem::path configPath;
    Json config;
    RunLauncher launcher;
    MenuBinding binding;
    Host(const std::filesystem::path& path):configPath(path),config(Read(path)),
      launcher(config.at("app_data").get<std::string>(),
        [this](const std::string& seed,const auto& progress) {
            const auto dir=std::filesystem::path(config.at("requests").get<std::string>())/Nonce();
            Run({config.at("generator"),seed.empty()?Nonce():seed,dir.string()},progress);
            return Text(dir/"seed.json");
        },
        [this](const std::string& seed,const auto& progress) {
            const auto root=std::filesystem::path(config.at("requests").get<std::string>())/Nonce();
            std::filesystem::create_directory(root);
            {std::ofstream out(root/"seed.json");out.exceptions(std::ios::badbit|std::ios::failbit);out<<seed;out.close();}
            Run({config.at("python"),config.at("prepare_script"),"--config",configPath.string(),
                 "--seed",(root/"seed.json").string(),"--result",(root/"prepared.json").string()},progress);
            auto result=Read(root/"prepared.json");
            return PreparedRun{result.at("manifest").get<std::string>(),result.at("module").get<std::string>()};
        },
        [this](unsigned slot) {
            auto run=RunCatalog(config.at("app_data").get<std::string>()).Read(slot);
            auto result=Read(std::filesystem::path(config.at("artifacts").get<std::string>())/run.seedHash/"ready.json");
            return PreparedRun{result.at("manifest").get<std::string>(),result.at("module").get<std::string>()};
        },true),
      binding(launcher,RetunedFrontend::RandomizerMenu,[]{return RetunedFrontend::StartupVisible;},
        [this](const LaunchRequest& request) {
            Write(config.at("handoff").get<std::string>(),Json{{"mode","randomizer"},
                {"manifest",request.prepared.manifest.string()},{"module",request.prepared.module.string()},
                {"profile",request.run.profile.string()},{"slot",request.menuSlot},{"seed",request.run.seed}});
            SDL_Event event{};event.type=SDL_QUIT;return SDL_PushEvent(&event)==1;
        }) {
        auto& menu=RetunedFrontend::RandomizerMenu;
        menu.StartNormal=[this] {
            Write(config.at("handoff").get<std::string>(),Json{{"mode","normal"}});
            SDL_Event event{};event.type=SDL_QUIT;SDL_PushEvent(&event);
        };
        if(const char* slot=getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) {
            menu.ActiveSlot=std::stoi(slot);
            menu.ActiveSeed=RunCatalog(config.at("app_data").get<std::string>()).Read(menu.ActiveSlot).seed;
            menu.SelectedAtStartup=true;
            RetunedFrontend::StartupVisible=false;
        } else if(getenv("RETUNED_RANDOMIZER_START_NORMAL"))RetunedFrontend::StartupVisible=false;
    }
};
}
inline void TickPrivateLauncher() {
    const char* path=getenv("RETUNED_RANDOMIZER_LAUNCHER");if(!path)return;
    static std::unique_ptr<Private::Host> host;
    static std::unique_ptr<Private::NativeHost> nativeHost;
    static bool failed=false;
    if(failed)return;
    try {
        if(!host && !nativeHost) {
            if(Private::Read(path).contains("installed_runtime"))nativeHost=std::make_unique<Private::NativeHost>(path);
            else host=std::make_unique<Private::Host>(path);
        }
        if(nativeHost)nativeHost->launcher.Poll();else host->binding.Poll();
    }
    catch(const std::exception& error){failed=true;std::fprintf(stderr,"Randomizer launcher: %s\n",error.what());}
}
}
