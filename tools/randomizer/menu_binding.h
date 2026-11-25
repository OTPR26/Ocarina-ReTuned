#pragma once
#include "run_launcher.h"
#if __has_include("fast/oot3d/retuned_randomizer_model.h")
#include "fast/oot3d/retuned_randomizer_model.h"
#else
#include "../frontend/randomizer_model.h"
#endif

namespace RetunedRandomizer {
// Construct and poll on the frontend thread. Launch queues a fresh guest;
// never replace the seed in an already running guest.
class MenuBinding {
public:
    using Launch = std::function<bool(const LaunchRequest&)>;
    MenuBinding(RunLauncher& launcher, RetunedFrontend::RandomizerMenuState& menu,
                std::function<bool()> atStartup, Launch launch)
        : launcher_(launcher), menu_(menu), startup_(std::move(atStartup)), launch_(std::move(launch)) {
        if (!startup_ || !launch_) throw std::invalid_argument("Missing randomizer menu host");
        if (menu_.Available()) throw std::invalid_argument("Randomizer menu already bound");
        menu_.Refresh = [this] { Refresh(); };
        menu_.Create = [this](unsigned slot, const std::string& seed) {
            if (menu_.CanCreate(slot, startup_()) && launcher_.Create(slot, seed)) { message_.clear(); UpdateStatus(); }
        };
        menu_.Start = [this](unsigned slot) {
            if (menu_.CanStart(slot, startup_()) && launcher_.Continue(slot)) { message_.clear(); UpdateStatus(); }
        };
        menu_.Import = [this](unsigned slot,const std::string& bundle) {
            if(menu_.CanCreate(slot,startup_()) && launcher_.Import(slot,bundle)) {
                message_.clear();UpdateStatus();
            }
        };
        menu_.Export = [this](unsigned slot) {
            if(!menu_.CanStart(slot,startup_()))
                throw std::runtime_error("Return to startup before exporting a run");
            return launcher_.Export(slot);
        };
        Refresh();
    }
    ~MenuBinding() {
        menu_.Refresh = {}; menu_.Create = {}; menu_.Start = {};
        menu_.Import = {}; menu_.Export = {};
        launcher_.Cancel();
    }
    MenuBinding(const MenuBinding&) = delete;
    MenuBinding& operator=(const MenuBinding&) = delete;
    void Poll() {
        const bool wasBusy = launcher_.Busy();
        auto request = launcher_.Poll();
        if (wasBusy && !launcher_.Busy()) Refresh();
        else UpdateStatus();
        if (!request) return;
        if (!startup_()) {
            menu_.Status = message_ = "Run is ready. Return to startup to open it.";
            return;
        }
        try {
            if (!launch_(*request)) throw std::runtime_error("Could not open the run. Its saves have been preserved.");
            handoff_ = true;
            menu_.Busy = true;
            menu_.Status = message_ = "Opening randomized game…";
        } catch (const std::exception& error) { menu_.Status = message_ = error.what(); }
    }
private:
    void UpdateStatus() {
        menu_.Busy = launcher_.Busy() || handoff_;
        menu_.Status = message_.empty() ? launcher_.Status() : message_;
    }
    void Refresh() {
        const auto slots = launcher_.Slots();
        for (unsigned i = 0; i < slots.size(); ++i) {
            auto& view = menu_.Slots[i];
            view.Status = slots[i].status == RunStatus::Empty ? RetunedFrontend::RandomizerSlotStatus::Empty :
                slots[i].status == RunStatus::Ready ? RetunedFrontend::RandomizerSlotStatus::Ready :
                RetunedFrontend::RandomizerSlotStatus::Unavailable;
            view.Seed = slots[i].seed; view.Message = slots[i].error;
        }
        UpdateStatus();
    }
    RunLauncher& launcher_;
    RetunedFrontend::RandomizerMenuState& menu_;
    std::function<bool()> startup_;
    Launch launch_;
    bool handoff_ = false;
    std::string message_;
};
}
