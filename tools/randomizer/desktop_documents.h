#pragma once
#include "transfer_files.h"
#include "menu_binding.h"
#include <imgui.h>
#include <algorithm>
#include <array>

namespace RetunedRandomizer {
// Draws inside the existing frontend; no secondary application or subprocess.
class DesktopDocuments {
public:
    DesktopDocuments(RetunedFrontend::RandomizerMenuState& menu,std::filesystem::path directory,
                     std::function<bool()> startup)
      :menu_(menu),directory_(std::move(directory)),startup_(std::move(startup)) {
        menu_.ChooseImport=[this](unsigned slot){Open(slot,false);};
        menu_.ChooseExport=[this](unsigned slot){Open(slot,true);};
        menu_.DrawTransfer=[this]{Draw();};
    }
    ~DesktopDocuments(){menu_.ChooseImport={};menu_.ChooseExport={};menu_.DrawTransfer={};}
    DesktopDocuments(const DesktopDocuments&)=delete;
private:
    static std::string Text(const std::filesystem::path& p) {
        const auto text=p.u8string();return {text.begin(),text.end()};
    }
    static std::filesystem::path Path(const char* text) {return std::filesystem::u8path(text);}
    void Open(unsigned slot,bool exporting) {
        if(exporting ? !menu_.CanStart(slot,startup_()) : !menu_.CanCreate(slot,startup_()))return;
        slot_=slot;exporting_=exporting;open_=true;pending_=true;error_.clear();
        std::snprintf(filename_.data(),filename_.size(),"randomizer-slot-%u.retuned-run",slot+1);
        Refresh();
    }
    void Refresh() {
        entries_.clear();error_.clear();
        std::snprintf(location_.data(),location_.size(),"%s",Text(directory_).c_str());
        std::error_code error;
        std::filesystem::directory_iterator it(directory_,error),end;
        unsigned count=0;
        for(;!error && it!=end;it.increment(error)) {
            if(++count>4096){error_="Large folder; enter the file path directly.";break;}
            std::error_code entryError;
            const bool folder=it->is_directory(entryError);
            if(!entryError && (folder || (!exporting_ && it->path().extension()==".retuned-run")))
                entries_.push_back({it->path(),folder});
        }
        if(error)error_="Cannot read this folder.";
        std::sort(entries_.begin(),entries_.end(),[](const Entry& a,const Entry& b){
            return a.folder!=b.folder?a.folder>b.folder:a.path.filename()<b.path.filename();
        });
    }
    void Complete(const std::filesystem::path& path) {
        try {
            if(exporting_) {
                WriteRunDocument(path,menu_.Export(slot_));
            } else {
                if(!menu_.CanCreate(slot_,startup_()))throw std::runtime_error("This slot is no longer empty");
                menu_.Import(slot_,ReadRunDocument(path));
            }
            open_=false;ImGui::CloseCurrentPopup();
        }catch(const std::exception& error){error_=error.what();}
    }
    void Draw() {
        if(pending_){ImGui::OpenPopup("Randomizer run file");pending_=false;}
        ImGui::SetNextWindowSize({ImGui::GetFontSize()*30,ImGui::GetFontSize()*24},ImGuiCond_Appearing);
        if(!ImGui::BeginPopupModal("Randomizer run file",nullptr,ImGuiWindowFlags_NoSavedSettings))return;
        if(!open_ || !startup_()){open_=false;ImGui::CloseCurrentPopup();ImGui::EndPopup();return;}
        ImGui::TextUnformatted(exporting_?"Export run":"Import run");
        ImGui::SetNextItemWidth(-1);
        const bool entered=ImGui::InputText("##location",location_.data(),location_.size(),ImGuiInputTextFlags_EnterReturnsTrue);
        if(ImGui::Button("Open path") || entered) {
            const auto path=Path(location_.data());std::error_code error;
            if(std::filesystem::is_directory(path,error)){directory_=path;Refresh();}
            else if(!exporting_)Complete(path);
            else error_="Choose a folder for export.";
        }
        ImGui::SameLine();if(ImGui::Button("Up")){directory_=directory_.parent_path();Refresh();}
        std::optional<std::filesystem::path> selected;
        const float footer=ImGui::GetFrameHeightWithSpacing()*(exporting_?3.f:2.f)+ImGui::GetFontSize()*2;
        const float height=std::max(ImGui::GetFontSize()*3,ImGui::GetContentRegionAvail().y-footer);
        if(ImGui::BeginChild("Files",{0,height},true)) {
            for(const auto& entry:entries_) {
                const auto label=(entry.folder?"[Folder] ":"")+Text(entry.path.filename());
                if(ImGui::Selectable(label.c_str())){selected=entry.path;break;}
            }
        }
        ImGui::EndChild();
        if(selected) {
            std::error_code error;
            if(std::filesystem::is_directory(*selected,error)){directory_=*selected;Refresh();}
            else Complete(*selected);
        }
        if(exporting_) {
            ImGui::InputText("Filename",filename_.data(),filename_.size());
            if(ImGui::Button("Export")) {
                const auto name=Path(filename_.data());
                if(name.empty() || name.has_parent_path() || name.extension()!=".retuned-run")
                    error_="Use a filename ending in .retuned-run.";
                else Complete(directory_/name);
            }
            ImGui::SameLine();
        }
        if(ImGui::Button("Cancel")){open_=false;ImGui::CloseCurrentPopup();}
        if(!error_.empty())ImGui::TextWrapped("%s",error_.c_str());
        ImGui::EndPopup();
    }
    struct Entry {std::filesystem::path path;bool folder;};
    RetunedFrontend::RandomizerMenuState& menu_;
    std::filesystem::path directory_;
    std::function<bool()> startup_;
    std::vector<Entry> entries_;
    std::array<char,2048> location_{};
    std::array<char,256> filename_{};
    std::string error_;
    unsigned slot_=0;
    bool exporting_=false,open_=false,pending_=false;
};
}
