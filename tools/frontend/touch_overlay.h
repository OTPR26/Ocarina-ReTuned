// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_touch_model.h"
#include "retuned_blue_style.h"
#include "retuned_frontend_state.h"
#include "fast/oot3d/graphics_settings_window.h"
#include "ship/Context.h"
#include "ship/config/Config.h"
#include <SDL.h>
#include <imgui.h>
#include <mutex>
#include <atomic>
#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif
namespace RetunedFrontend {
inline constexpr bool TouchPlatform() {
#if defined(__ANDROID__) || (defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV)
 return true;
#else
 return false;
#endif
}
inline TouchModel MobileTouch;
inline std::mutex TouchMutex;
inline std::atomic<bool> TouchEnabled{TouchPlatform()};
inline bool TouchInputActive=false;
inline float TouchOpacity=.28f;
inline void SetTouchActive(bool active) {
 std::lock_guard lock(TouchMutex);
 if(TouchInputActive!=active)MobileTouch.Reset();
 TouchInputActive=active;
}
inline int WatchTouch(void*,SDL_Event* event) {
 if(!NativeFrontendEnabled||!TouchPlatform())return 1;
 std::lock_guard lock(TouchMutex);
 if(event->type==SDL_APP_WILLENTERBACKGROUND || (event->type==SDL_WINDOWEVENT&&event->window.event==SDL_WINDOWEVENT_FOCUS_LOST))MobileTouch.Reset();
 if(!TouchInputActive)return 1;
 switch(event->type) {
 case SDL_FINGERDOWN:MobileTouch.Down(event->tfinger.fingerId,event->tfinger.x,event->tfinger.y,TouchEnabled);break;
 case SDL_FINGERMOTION:MobileTouch.Motion(event->tfinger.fingerId,event->tfinger.x,event->tfinger.y);break;
 case SDL_FINGERUP:MobileTouch.Up(event->tfinger.fingerId);break;
 }
 return 1;
}
inline void InitializeTouch() {
 static bool watching=false;
 if(TouchPlatform()&&!watching){SDL_AddEventWatch(WatchTouch,nullptr);watching=true;}
 auto config=Ship::Context::GetRawInstance()->GetConfig();
 TouchEnabled=config->GetBool("Touch.Enabled",TouchPlatform());
 TouchOpacity=std::clamp(config->GetFloat("Touch.Opacity",.28f),.1f,.75f);
}
inline TouchSnapshot SampleTouch(bool consume) {
 std::lock_guard lock(TouchMutex);return MobileTouch.Sample(consume);
}
inline void DrawTouch(bool settingsVisible) {
 if(!NativeFrontendEnabled||!TouchPlatform())return;
 const bool active=!StartupVisible&&!settingsVisible;
 SetTouchActive(active);
 const auto* v=ImGui::GetMainViewport();
 {std::lock_guard lock(TouchMutex);MobileTouch.SetAspect(v->Size.x/std::max(v->Size.y,1.f));}
 if(!active)return;
 const auto state=SampleTouch(false);auto* draw=ImGui::GetForegroundDrawList();
 for(const auto& c:TouchLayout) {
  if(!TouchEnabled&&c.Action!=TouchAction::Settings)continue;
  const ImVec2 center{v->Pos.x+c.X*v->Size.x,v->Pos.y+c.Y*v->Size.y};
  const float radius=c.Radius*v->Size.y;
  const bool held=(state.Buttons&TouchModel::Bit(c.Action))!=0;
  draw->AddCircleFilled(center,radius,ImGui::GetColorU32(ImVec4(.05f,.12f,.20f,held?TouchOpacity+.2f:TouchOpacity)));
  draw->AddCircle(center,radius,ImGui::GetColorU32(ImVec4(.75f,.86f,1,held?.9f:.45f)),0,1.5f);
  if(c.Action==TouchAction::Move||c.Action==TouchAction::Look) {
   const float x=c.Action==TouchAction::Move?state.MoveX:state.LookX;
   const float y=c.Action==TouchAction::Move?state.MoveY:state.LookY;
   draw->AddCircleFilled({center.x+x*radius*.65f,center.y-y*radius*.65f},radius*.38f,ImGui::GetColorU32(ImVec4(.7f,.82f,1,.35f)));
  } else {
   const float font=std::min(radius*.65f,ImGui::GetFontSize()*1.2f);
   const ImVec2 size=ImGui::GetFont()->CalcTextSizeA(font,1000,0,c.Label);
   draw->AddText(ImGui::GetFont(),font,{center.x-size.x*.5f,center.y-size.y*.5f},IM_COL32(230,241,255,200),c.Label);
  }
 }
}
inline void DrawTouchSettings() {
 if(!TouchPlatform()){ImGui::TextWrapped("Touch controls are available on iPhone, iPad and Android. Use Select / View / Minus or L3 + R3 for settings with a controller.");return;}
 auto config=Ship::Context::GetRawInstance()->GetConfig();
 bool enabled=TouchEnabled.load();
 if(Toggle("Show touch controls",&enabled)){TouchEnabled.store(enabled);config->SetBool("Touch.Enabled",enabled);config->Save();}
 if(ImGui::SliderFloat("Opacity",&TouchOpacity,.1f,.75f,"%.2f")){config->SetFloat("Touch.Opacity",TouchOpacity);config->Save();}
 ImGui::TextWrapped("Left stick: movement. Right stick: camera. L / R: items. ZL / ZR: targeting and shield. Start: inventory. Settings remains available when controls are hidden.");
}
}
