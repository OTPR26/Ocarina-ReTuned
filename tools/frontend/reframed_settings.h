#pragma once
#include "oot3d_native_a32_process.h"
#include "retuned_ocarina_lifecycle.h"
#include "retuned_touch_hud_runtime.h"
#include "fast/oot3d/retuned_blue_style.h"
#include "fast/oot3d/graphics_settings_window.h"
#include "ship/Context.h"
#include "ship/config/Config.h"
#include <nlohmann/json.hpp>
#include <imgui.h>
#include <array>
#include <algorithm>
#include <filesystem>
#include <stdexcept>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <string>

namespace RetunedFrontend {
inline constexpr std::array<const char*,9> Keys{
    "targeting", "first_person_camera", "motion_control", "hud_size", "camera_distance",
    "camera_inversion", "movement_speed", "roll_speed", "roll_recovery"};
inline constexpr std::array<int,9> Counts{2,2,2,4,7,4,3,3,3};
inline bool Valid(const std::array<int,9>& values) {
    for(size_t i=0;i<values.size();++i) if(values[i]<0 || values[i]>=Counts[i])return false;
    return true;
}
class Settings {
  public:
    void Initialize(const std::filesystem::path& manifest) {
        std::lock_guard lock(mMutex);
        try {
            std::ifstream stream(manifest);
            nlohmann::json root;stream>>root;
            mBridge=root.at("reframed_frontend");
            auto config=Ship::Context::GetRawInstance()->GetConfig()->GetNestedJson();
            if(config.contains("Reframed")) {
                const auto& stored=config.at("Reframed");
                if(stored.at("schema")!=1)throw std::runtime_error("Unsupported Reframed settings version");
                for(size_t i=0;i<Keys.size();++i)mValues[i]=stored.at(Keys[i]).get<int>();
                if(!Valid(mValues))throw std::runtime_error("Invalid Reframed settings");
                mManualJump=stored.value("manual_jump",0);
                if(mManualJump<0 || mManualJump>2)mManualJump=0;
                mConfigured=true;
            }
            mReady=true;
            TouchManualJumpMode=0;
        } catch(const std::exception& e){mError=e.what();}
    }
    bool Ready()const{std::lock_guard lock(mMutex);return mReady;}
    std::string Error()const{std::lock_guard lock(mMutex);return mError;}
    int Value(size_t index)const{std::lock_guard lock(mMutex);return mValues.at(index);}
    void Set(size_t index,int value) {
        std::lock_guard lock(mMutex);
        auto changed=mValues;changed.at(index)=value;
        if(!Valid(changed))return;
        nlohmann::json saved{{"schema",1}};
        for(size_t i=0;i<Keys.size();++i)saved[Keys[i]]=changed[i];
        saved["manual_jump"]=mManualJump;
        if(!Ship::Context::GetRawInstance()->GetConfig()->SetBlock("Reframed",saved)) {
            mError="Could not save settings. Your previous selection remains active.";return;
        }
        mValues=changed;mConfigured=true;mError.clear();
    }
    bool HasManualJump()const {
        std::lock_guard lock(mMutex);
        return mReady && mBridge.at("functions").contains("ManualJump_Set");
    }
    int ManualJump()const{std::lock_guard lock(mMutex);return mManualJump;}
    void SetManualJump(int value) {
        std::lock_guard lock(mMutex);
        if(value<0 || value>2)return;
        nlohmann::json saved{{"schema",1},{"manual_jump",value}};
        for(size_t i=0;i<Keys.size();++i)saved[Keys[i]]=mValues[i];
        if(!Ship::Context::GetRawInstance()->GetConfig()->SetBlock("Reframed",saved)) {
            mError="Could not save settings. Your previous selection remains active.";return;
        }
        mManualJump=value;mError.clear();
    }
    void Apply(Oot3dNativeGame::NativeA32Process& process) {
        std::lock_guard lock(mMutex);
        if(!mReady)return;
        auto& memory=process.Memory();uint32_t context=0;
        if(!memory.Read32(mBridge.at("context_pointer").get<uint32_t>(),&context) || !context)return;
        const auto save=mBridge.at("save_context").get<uint32_t>();
        const auto invoke=[&](const char* name,std::span<const uint32_t> args={}) {
            const auto entry=mBridge.at("functions").at(name).get<uint32_t>();
            uint32_t result=0;std::string error;
            if(!memory.IsExecutable(entry,4) || !process.InvokeFunctionWithResult(entry,args,0xFFFF0000U,&result,&error))
                throw std::runtime_error(std::string("Reframed setting could not be applied: ")+name+" "+error);
            return result;
        };
        try {
            if(mBridge.at("functions").contains("InputRemap_IsOcarinaUiReady")) {
                const bool open=invoke("InputRemap_IsOcarinaUiOpen")!=0;
                const bool ready=open && invoke("InputRemap_IsOcarinaUiReady")!=0;
                if(mOcarina.Finished(open,ready))invoke("InputRemap_CloseOcarinaUi");
            }
            if(!mConfigured) {
                constexpr std::array<uint32_t,3> offsets{0x2D,0x13D8,0xF};
                for(size_t i=0;i<3;++i){uint8_t v=0;if(!memory.Read8(save+offsets[i],&v))return;mValues[i]=v&1;}
                const auto hud=invoke("NativeHud_GetScalePercent");
                mValues[3]=hud==0?0:hud==75?1:hud==125?3:2;
                mValues[4]=invoke("Camera_GetDistanceOption");mValues[5]=invoke("Camera_GetControlMode");
                for(uint32_t i=0;i<3;++i)mValues[6+i]=invoke("MovementOptions_Get",std::span<const uint32_t>(&i,1));
                if(!Valid(mValues))throw std::runtime_error("Invalid settings returned by Reframed");
                Set(0,mValues[0]);
                if(!mConfigured)return;
            }
            constexpr std::array<uint32_t,3> offsets{0x2D,0x13D8,0xF};
            for(size_t i=0;i<3;++i)if(!memory.Write8(save+offsets[i],static_cast<uint8_t>(mValues[i])))
                throw std::runtime_error("Game options are not writable");
            if(!mApplied || mValues!=mPrevious) {
                constexpr std::array<uint32_t,4> sizes{0,75,100,125};
                uint32_t value=sizes[mValues[3]];invoke("NativeHud_SetScalePercent",{&value,1});
                value=mValues[4];invoke("Camera_SetDistanceOption",{&value,1});
                value=mValues[5];invoke("Camera_SetControlMode",{&value,1});
                for(uint32_t i=0;i<3;++i){const std::array<uint32_t,2> args{i,uint32_t(mValues[6+i])};invoke("MovementOptions_Set",args);}
                mPrevious=mValues;mApplied=true;
            }
            if(mBridge.at("functions").contains("ManualJump_Set") && mManualJumpApplied!=mManualJump) {
                uint32_t value=static_cast<uint32_t>(mManualJump);
                invoke("ManualJump_Set",{&value,1});mManualJumpApplied=mManualJump;
            }
            // Native inventory/instrument controls retain their original meaning.
            uint8_t touchPause=1,touchInstrument=1;
            const bool jumpGameplay=NativeTouchHud.Ready() &&
                memory.Read8(NativeTouchHud.PauseLayout,&touchPause) &&
                memory.Read8(NativeTouchHud.OcarinaLayout,&touchInstrument) && !touchPause && !touchInstrument;
            TouchManualJumpMode=jumpGameplay && mManualJumpApplied>=0?mManualJumpApplied:0;
            const bool touchHud=NativeTouchHud.Ready()&&TouchHudActive.load();
            if(touchHud||mTouchHudApplied){
                constexpr std::array<uint32_t,4> sizes{0,75,100,125};
                uint32_t value=sizes[mValues[3]];invoke("NativeHud_SetScalePercent",{&value,1});
            }
            mTouchHudApplied=touchHud;
        }catch(const std::exception& e){mError=e.what();mReady=false;}
    }
  private:
    OcarinaShortcutLifecycle mOcarina;
    mutable std::recursive_mutex mMutex;
    nlohmann::json mBridge;
    std::array<int,9> mValues{0,0,0,2,2,0,0,0,0},mPrevious{};
    int mManualJump=0,mManualJumpApplied=-1;
    bool mReady=false,mConfigured=false,mApplied=false,mTouchHudApplied=false;
    std::string mError;
};
inline Settings& Current(){static Settings instance;return instance;}
class Panel final:public Fast::Oot3d::GraphicsSettingsPanelTab {
  public:
    explicit Panel(std::string page):mPage(std::move(page)){}
    const char* Label()const noexcept override{return mPage.c_str();}
    void Draw()override {
        auto& settings=Current();
        if(!settings.Error().empty())ImGui::TextWrapped("%s",settings.Error().c_str());
        ImGui::BeginDisabled(!settings.Ready());
        auto combo=[&](size_t index,const char* label,const char* choices,const char* help){
            int value=settings.Value(index);
            if(index==2){bool enabled=value==0;if(Toggle("Motion aiming",&enabled))settings.Set(index,enabled?0:1);ImGui::Spacing();return;}
            ImGui::TextUnformatted(label);ImGui::SetNextItemWidth(std::min(ImGui::GetContentRegionAvail().x,ImGui::GetFontSize()*24));
            ImGui::PushID(static_cast<int>(index));
            if(ImGui::Combo("##value",&value,choices))settings.Set(index,value);
            ImGui::PopID();ImGui::PushStyleColor(ImGuiCol_Text,ImGui::GetStyleColorVec4(ImGuiCol_TextDisabled));ImGui::TextWrapped("%s",help);ImGui::PopStyleColor();ImGui::Spacing();
        };
        if(mPage=="Camera") {
            combo(4,"Camera distance","75%\0 87.5%\0 100%\0 112.5%\0 125%\0 137.5%\0 150%\0","Exploration camera; walls still limit distance.");
        }else if(mPage=="Reframed controls") {
            combo(0,"Targeting mode","Hold\0Switch\0","Choose how targeting stays active.");
            combo(1,"First-person camera","Normal\0Inverted\0","Vertical controls for looking and aiming.");
            combo(2,"Motion control","On\0Off\0","Motion aiming when a supported device supplies it.");
            combo(5,"Free-camera inversion","Normal\0Invert X\0Invert Y\0Invert both\0","Right-stick exploration camera.");
        }else if(mPage=="HUD") {
            combo(3,"HUD size","Hidden\0 75%\0 100%\0 125%\0","Changes gameplay HUD size independently of this menu.");
        }else if(mPage=="Quality of life") {
            combo(6,"Movement speed","Normal\0+10%\0+20%\0","Walking and running; other actions stay normal.");
            combo(7,"Roll speed","Normal\0+10%\0+20%\0","Increases roll speed and distance.");
            combo(8,"Roll recovery","Normal\0-10%\0-20%\0","Shortens the final recovery of a forward roll.");
            if(settings.HasManualJump()) {
                int jump=settings.ManualJump();
                ImGui::TextUnformatted("Manual jump");
                ImGui::SetNextItemWidth(std::min(ImGui::GetContentRegionAvail().x,ImGui::GetFontSize()*24));
                if(ImGui::Combo("##manual_jump",&jump,"Off\0ZR\0X\0"))settings.SetManualJump(jump);
                ImGui::TextWrapped("Jump while standing or moving on the ground. Choosing X moves its equipped item to ZR.");
            }
        }
        ImGui::EndDisabled();
    }
  private:std::string mPage;
};
}
