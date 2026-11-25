#include "run_launcher.h"
#include "generator.h"
#include "menu_binding.h"
#include "launch_arguments.h"
#include "../native/setup/game_handoff.h"
#include <triaevum/sha256.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <thread>
#include <iostream>
using namespace RetunedRandomizer;
namespace fs = std::filesystem;
using Json = nlohmann::json;
void Check(bool b) { if (!b) throw std::runtime_error("Launcher check failed"); }
std::string Hash(const std::string& bytes) {
    const char* hex = "0123456789abcdef"; std::string out;
    for (auto b : triaevum::module::detail::Sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(bytes.data()), bytes.size()))) {
        out += hex[b >> 4]; out += hex[b & 15];
    } return out;
}
void Write(const fs::path& path, const std::string& text) { std::ofstream(path) << text; }
std::optional<LaunchRequest> Finish(RunLauncher& launcher) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    while (launcher.Busy()) {
        if (auto request = launcher.Poll()) return request;
        Check(std::chrono::steady_clock::now() < deadline);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    } return std::nullopt;
}
int main() {
    const auto root = fs::temp_directory_path() / ("retuned-launch-test-" +
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(root);
    try {
        const auto seed = Generate("retuned-proof-001");
        const auto other = Generate("retuned-proof-002");
        const auto artifacts = root / "prepared"; fs::create_directory(artifacts);
        const std::string code = "fixture code", module = "fixture module";
        PreparedRun prepared{artifacts / "manifest.json", artifacts / "module.bin"};
        Write(artifacts / "code.bin", code); Write(prepared.module, module);
        auto bind = [&](const std::string& text) {
            Write(prepared.manifest, Json{{"source", {{"code_bin_path", "code.bin"},
                 {"code_bin_sha256", Hash(code)}}}, {"randomizer_proof", {{"schema", 1},
                 {"seed_sha256", Hash(text)}, {"activation_allowed", false},
                 {"extended_save_size", 1244}}}}.dump());
            Write(prepared.module.string() + ".randomizer.json", Json{
                {"format", "retuned-randomizer-module-v1"}, {"seed_sha256", Hash(text)},
                {"code_sha256", Hash(code)}, {"module_sha256", Hash(module)}}.dump());
        };
        bind(seed);
        const auto retained=artifacts/"retained-module.bin";
        fs::copy_file(prepared.module,retained);
        fs::copy_file(prepared.module.string()+".randomizer.json",retained.string()+".randomizer.json");
        const auto rejectsRuntime=[&](const auto& candidates,const auto& runtime,const auto& seedId,bool development) {
            bool rejected=false;
            try { ResolveRunRuntime(prepared.manifest,candidates,runtime,seedId,development); }
            catch(const std::exception&) { rejected=true; }
            Check(rejected);
        };
        Write(prepared.module,"updated module without matching binding");
        auto resolved=ResolveRunRuntime(prepared.manifest,{prepared.module,retained},Hash(code),Hash(seed),true);
        Check(resolved.module==retained);
        rejectsRuntime(std::vector<fs::path>{prepared.module},Hash(code),Hash(seed),true);
        rejectsRuntime(std::vector<fs::path>{retained},Hash(code),Hash(other),true);
        rejectsRuntime(std::vector<fs::path>{retained},Hash("another runtime"),Hash(seed),true);
        rejectsRuntime(std::vector<fs::path>{retained},Hash(code),Hash(seed),false);
        Write(prepared.module,module);
        Write(root / "save00.bin", "normal save");
        auto generate = [&](const auto&, const auto&) { return seed; };
        auto prepare = [&](const auto&, const auto&) { return prepared; };
        auto resolve = [&](unsigned) { return prepared; };
        RunLauncher production(root, generate, prepare, resolve);
        Check(production.Create(0, "test")); Check(!Finish(production));
        Check(production.Slots()[0].status == RunStatus::Empty);
        RunLauncher launcher(root, generate, prepare, resolve, true);
        // Wrong seed and damaged output fail before reserving a slot.
        bind(other); Check(launcher.Create(0, "test")); Check(!Finish(launcher));
        Check(launcher.Slots()[0].status == RunStatus::Empty);
        bind(seed); Write(prepared.module, "damaged");
        Check(launcher.Create(0, "test")); Check(!Finish(launcher));
        Check(launcher.Slots()[0].status == RunStatus::Empty);
        Write(prepared.module, module);
        Check(launcher.Create(0, "test")); Check(!launcher.Create(1, "test"));
        auto request = Finish(launcher); Check(request.has_value());
        Check(request->guestSlot == 0 && request->menuSlot == 0);
        Check(request->run.profile != root && request->run.seedHash == Hash(seed));
        const std::vector<std::string> normalArguments={"--a32-process-manifest","ordinary.json",
            "--title-plugin","ordinary.module","--save-data","ordinary-saves","--config","settings.json"};
        auto randomArguments=LaunchArguments(root,normalArguments,*request);
        Check(randomArguments[5]==request->run.profile.string());
        Check(normalArguments[5]=="ordinary-saves" && randomArguments[7]=="settings.json");
        const auto rejectLaunch=[&](auto arguments,auto invalidRequest) {
            bool rejected=false;
            try { LaunchArguments(root,std::move(arguments),invalidRequest); }
            catch(const std::exception&) { rejected=true; }
            Check(rejected);
        };
        auto duplicate=normalArguments;
        duplicate.insert(duplicate.end(),{"--save-data","another-profile"});
        rejectLaunch(duplicate,*request);
        auto missing=normalArguments;missing.erase(missing.begin()+4,missing.begin()+6);
        rejectLaunch(missing,*request);
        auto wrongRun=*request;wrongRun.run.seedHash=std::string(64,'0');
        rejectLaunch(normalArguments,wrongRun);
        wrongRun=*request;wrongRun.run.profile=root;
        rejectLaunch(normalArguments,wrongRun);
        RetunedSetup::GameHandoff handoff;
        Check(!handoff.Queue({{},0,false}));
        Check(!handoff.Queue({normalArguments,3,false}));
        Check(!handoff.Queue({normalArguments,-1,true}));
        Check(!handoff.Queue({{std::string("bad\0argument",12)},0,false}));
        Check(handoff.Queue({randomArguments,0,false}));
        Check(!handoff.Queue({normalArguments,-1,false}));
        auto next=handoff.Take();Check(next && next->arguments==randomArguments);
        Check(!handoff.Take());
        Check(handoff.Queue({normalArguments,-1,false}));handoff.Cancel();Check(!handoff.Take());
        Check(!launcher.Create(0, "test"));
        Check(launcher.Continue(0)); Check(Finish(launcher).has_value());
        bind(other); Check(launcher.Continue(0)); Check(!Finish(launcher));
        Check(launcher.Slots()[0].status == RunStatus::Ready);
        bind(seed);
        std::promise<void> started, release;
        auto gate = release.get_future();
        RunLauncher cancelled(root, [&](const auto&, const auto& progress) {
            started.set_value(); gate.wait(); progress("Generating"); return seed;
        }, prepare, resolve, true);
        Check(cancelled.Create(1, "test")); started.get_future().wait();
        cancelled.Cancel(); release.set_value(); Check(!Finish(cancelled));
        Check(cancelled.Slots()[1].status == RunStatus::Empty);
        Check(cancelled.Status().find("cancelled") != std::string::npos);
        std::ifstream normal(root / "save00.bin"); std::string text;
        std::getline(normal, text); Check(text == "normal save");
        // Two data-only seeds can share a compiled module; seed and layout
        // identities remain independent, and both are checked on Continue.
        auto sharedBind = [&](const std::string& text) {
            auto manifest=Json::parse(std::ifstream(prepared.manifest));
            manifest["randomizer_proof"]["seed_sha256"]=Hash(text);
            manifest["randomizer_proof"]["seed_layout"]={{"schema",1},{"symbols",Json::object()}};
            manifest["randomizer_proof"]["seed_file"]="seed.json";
            Write(prepared.manifest,manifest.dump());
            Write(artifacts/"seed.json",text);
            Write(prepared.module.string()+".randomizer.json",Json{
                {"format","retuned-randomizer-module-v2"},
                {"seed_layout_sha256",Hash(manifest["randomizer_proof"]["seed_layout"].dump())},
                {"code_sha256",Hash(code)},{"module_sha256",Hash(module)}}.dump());
        };
        sharedBind(seed);
        Check(launcher.Continue(0));Check(Finish(launcher).has_value());
        Write(artifacts/"seed.json",other);
        Check(launcher.Continue(0));Check(!Finish(launcher));
        sharedBind(seed);
        auto broken=Json::parse(std::ifstream(prepared.manifest));
        broken["randomizer_proof"]["seed_layout"]["schema"]=2;
        Write(prepared.manifest,broken.dump());
        Check(launcher.Continue(0));Check(!Finish(launcher));
        bind(seed);
        SaveStore saved(request->run.profile,request->run.seedHash,request->run.runtimeHash,1244,false);
        Bytes native(0x14dc,7),extended(1244,8);
        saved.Commit(0,native,extended);
        const auto exported=launcher.Export(0);
        Check(!launcher.Import(0,exported));
        Check(launcher.Import(1,exported));
        auto imported=Finish(launcher);Check(imported.has_value());
        Check(imported->menuSlot==1 && imported->run.profile!=request->run.profile);
        Check(launcher.Export(1)==exported);
        Check(launcher.Continue(1));Check(Finish(launcher).has_value());
        Check(launcher.Import(2,"broken"));Check(!Finish(launcher));
        Check(launcher.Slots()[2].status==RunStatus::Empty);
        bool startup = false, launched = false;
        RetunedFrontend::RandomizerMenuState menu;
        {
            MenuBinding binding(launcher, menu, [&] { return startup; },
                [&](const LaunchRequest& selected) {
                    Check(selected.run.profile == request->run.profile);
                    launched = true; return true;
                });
            Check(menu.Available());
            menu.Start(0); Check(!launcher.Busy()); // Never switch a live guest.
            menu.Import(2,exported);Check(!launcher.Busy());
            bool rejected=false;
            try{menu.Export(0);}catch(const std::exception&){rejected=true;}
            Check(rejected);
            startup = true;Check(menu.Export(0)==exported);
            menu.Start(0); Check(menu.Busy);
            while (launcher.Busy()) {
                binding.Poll();
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            Check(launched && menu.Busy); // Prevent a second launch during handoff.
            menu.Start(0); Check(!launcher.Busy());
        }
        Check(!menu.Available() && !menu.Import && !menu.Export);
        fs::remove_all(root);
        std::cerr << "Launch identity, module corruption, cancellation, and save isolation passed.\n";
    } catch (...) { fs::remove_all(root); throw; }
}
