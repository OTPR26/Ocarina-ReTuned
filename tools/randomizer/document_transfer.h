#pragma once
#if __has_include("fast/oot3d/retuned_randomizer_model.h")
#include "fast/oot3d/retuned_randomizer_model.h"
#else
#include "../frontend/randomizer_model.h"
#endif
#include <optional>
#include <stdexcept>
#include <utility>

namespace RetunedRandomizer {
struct DocumentResult {
    unsigned slot;
    bool exporting, cancelled;
    std::string bytes, error;
};

// All callbacks run on the frontend thread. The platform owns its file picker.
class DocumentTransfer {
public:
    using Begin = std::function<bool(unsigned,bool,const std::string&)>;
    using Take = std::function<std::optional<DocumentResult>()>;
    static constexpr std::size_t Limit = 10*1024*1024;
    DocumentTransfer(RetunedFrontend::RandomizerMenuState& menu,
                     std::function<bool()> startup, Begin begin, Take take)
      :menu_(menu),startup_(std::move(startup)),begin_(std::move(begin)),take_(std::move(take)) {
        menu_.ChooseImport=[this](unsigned slot){Open(slot,false);};
        menu_.ChooseExport=[this](unsigned slot){Open(slot,true);};
    }
    ~DocumentTransfer() {
        menu_.ChooseImport={};menu_.ChooseExport={};menu_.TransferBusy=false;
    }
    DocumentTransfer(const DocumentTransfer&)=delete;
    void Poll() {
        if(!pending_)return;
        try {
            auto result=take_();
            if(!result || !pending_)return;
            const auto expected=*pending_;
            pending_.reset();menu_.TransferBusy=false;
            if(result->slot!=expected.first || result->exporting!=expected.second)
                throw std::runtime_error("Unexpected randomizer document result");
            if(result->cancelled){menu_.TransferStatus.clear();return;}
            if(!result->error.empty())throw std::runtime_error(result->error);
            if(!startup_())throw std::runtime_error("Return to startup before importing or exporting runs");
            if(!result->exporting) {
                if(!menu_.CanCreate(result->slot,true) || !menu_.Import)
                    throw std::runtime_error("This randomizer slot is no longer available");
                if(result->bytes.empty() || result->bytes.size()>Limit)
                    throw std::runtime_error("Invalid randomizer document size");
                // The run importer validates the seed, runtime, and save bundle.
                menu_.Import(result->slot,result->bytes);
                menu_.TransferStatus.clear();
            } else menu_.TransferStatus="Run exported.";
        } catch(const std::exception& error) {
            pending_.reset();menu_.TransferBusy=false;menu_.TransferStatus=error.what();
        }
    }
private:
    void Open(unsigned slot,bool exporting) {
        if(pending_ || (exporting ? !menu_.CanStart(slot,startup_()) : !menu_.CanCreate(slot,startup_())))return;
        try {
            if(exporting ? !bool(menu_.Export) : !bool(menu_.Import))
                throw std::runtime_error("Run transfer is unavailable");
            const auto bytes=exporting?menu_.Export(slot):std::string{};
            if(exporting && (bytes.empty() || bytes.size()>Limit))
                throw std::runtime_error("Invalid randomizer document size");
            if(!begin_(slot,exporting,bytes))throw std::runtime_error("Could not open the document picker");
            pending_=std::make_pair(slot,exporting);menu_.TransferBusy=true;
            menu_.TransferStatus=exporting?"Exporting run…":"Choose a run to import…";
        } catch(const std::exception& error){menu_.TransferStatus=error.what();}
    }
    RetunedFrontend::RandomizerMenuState& menu_;
    std::function<bool()> startup_;
    Begin begin_;
    Take take_;
    std::optional<std::pair<unsigned,bool>> pending_;
};
}
