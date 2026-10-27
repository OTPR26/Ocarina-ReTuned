// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "ship/audio/retuned_output_gain.h"
#include "retuned_touch_model.h"
#include "retuned_touch_visibility.h"
#include "retuned_touch_hud_state.h"
#include "retuned_blue_style.h"
#include "retuned_frontend_state.h"
#include "retuned_responsive_layout.h"
#include "fast/oot3d/graphics_settings_window.h"
#include "ship/Context.h"
#include "ship/config/Config.h"
#include <SDL.h>
#include <imgui.h>
#include <mutex>
#include <atomic>
#ifdef __ANDROID__
#include <jni.h>
#endif
#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IOS && !TARGET_OS_TV
extern "C" void RetunedIOS_SetTouchControlsEnabled(int enabled);
extern "C" void RetunedIOS_EditTouchLayout(void);
extern "C" void RetunedIOS_SetTouchOpacity(float opacity);
extern "C" void RetunedIOS_SetTouchScale(float scale);
extern "C" void RetunedIOS_SetExtraShoulders(int enabled);
extern "C" void RetunedIOS_SetManualJump(int mode);
extern "C" void RetunedIOS_SetTouchHudIcons(int enabled);
extern "C" void RetunedIOS_SetFaceButtonLayout(int layout);
extern "C" void RetunedIOS_SetTouchLeftStickFloating(int floating);
extern "C" void RetunedIOS_SetTouchControlsMenuVisible(int visible);
#endif
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
inline NativeTouchState NativeTouch;
inline std::mutex TouchMutex;
inline TouchVisibilityState TouchVisibility{TouchPlatform()};
inline std::atomic<bool>& TouchEnabled=TouchVisibility.Configured;
inline bool TouchInputActive=false;
inline int TouchMenuMode=-1;
inline std::atomic<bool> TouchHostMenu{true};
inline std::atomic<int> TouchHostMode{1};
inline bool TouchSettingsWasDown=false;
inline float TouchOpacity=.28f;
inline std::atomic<float> NativeTouchOpacity{.28f},TouchSize{1.f};
inline std::atomic<bool> TouchFloating{true};
inline std::atomic<int> TouchFaceLayout{0};
inline std::atomic<bool> TouchExtraShoulders{false};
inline std::atomic<int> TouchZLAction{-1},TouchZRAction{-1};
inline void SetTouchActive(bool active) {
 std::lock_guard lock(TouchMutex);
 if(TouchInputActive!=active)MobileTouch.Reset();
 TouchInputActive=active;
}
inline int WatchTouch(void*,SDL_Event* event) {
 if(!NativeFrontendEnabled||!TouchPlatform())return 1;
#if defined(__ANDROID__) || (defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV)
 if(event->type==SDL_APP_WILLENTERBACKGROUND){std::lock_guard lock(TouchMutex);NativeTouch.Reset();}
 return 1;
#endif
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
 TouchIconOpacity=std::clamp(config->GetFloat("Touch.IconOpacity",1.f),0.f,1.f);
 TouchHudRequested=config->GetBool("Touch.ItemIcons",true);
 TouchVisibility.Configure(config->GetBool("Touch.Enabled",TouchPlatform()));
 TouchOpacity=std::clamp(config->GetFloat("Touch.Opacity",.28f),.1f,.75f);
 TouchSize=std::clamp(config->GetFloat("Touch.Scale",1.f),.75f,1.25f);
 TouchFloating=config->GetBool("Touch.Floating",true);
 TouchExtraShoulders=config->GetBool("Touch.ExtraShoulders",false);
 TouchZLAction=std::clamp(config->GetInt("Touch.ZLAction",-1),-1,15);
 TouchZRAction=std::clamp(config->GetInt("Touch.ZRAction",-1),-1,15);
 TouchFaceLayout=std::clamp(config->GetInt("Touch.FaceLayout",0),0,2);
 MenuSize=std::clamp(config->GetFloat("Interface.Scale",1.f),.8f,1.25f);
 Retuned::OutputVolume=Retuned::ValidVolume(config->GetFloat("Audio.Volume",1.f));
 Retuned::OutputMuted=config->GetBool("Audio.Muted",false);
}
inline TouchSnapshot SampleTouch(bool consume) {
 std::lock_guard lock(TouchMutex);
 if(!TouchVisibility.ControlsVisible()){MobileTouch.Reset();NativeTouch.Reset();return {};}
 auto state=MobileTouch.Sample(consume);const auto native=NativeTouch.Sample(consume);
 state.Buttons|=native.Buttons;state.Captured|=native.Captured;
 if(native.MoveX||native.MoveY){state.MoveX=native.MoveX;state.MoveY=native.MoveY;}
 if(native.LookX||native.LookY){state.LookX=native.LookX;state.LookY=native.LookY;}
 return state;
}
inline void MenuTouchInput(const TouchSnapshot& state,bool menu,bool settingsVisible) {
 auto& io=ImGui::GetIO();
 const auto held=[&](TouchAction action){return (state.Buttons&TouchModel::Bit(action))!=0;};
 // Keyboard navigation keeps touch independent of the physical gamepad that
 // SDL's backend may select for its own gamepad navigation events.
 const bool keys[]={menu&&(held(TouchAction::Up)||state.MoveY>.5f),menu&&(held(TouchAction::Down)||state.MoveY<-.5f),
  menu&&(held(TouchAction::Left)||state.MoveX<-.5f),menu&&(held(TouchAction::Right)||state.MoveX>.5f),
  menu&&(held(TouchAction::A)||held(TouchAction::Inventory)),menu&&held(TouchAction::B)};
 constexpr ImGuiKey bindings[]={ImGuiKey_UpArrow,ImGuiKey_DownArrow,ImGuiKey_LeftArrow,ImGuiKey_RightArrow,ImGuiKey_Enter,ImGuiKey_Escape};
 static bool previousKeys[6]{};
 for(unsigned i=0;i<6;++i)if(keys[i]!=previousKeys[i]){io.AddKeyEvent(bindings[i],keys[i]);previousKeys[i]=keys[i];}
 const bool settings=menu&&(held(TouchAction::Settings)||(settingsVisible&&held(TouchAction::B)&&!ImGui::IsAnyItemActive()&&!ImGui::IsPopupOpen(nullptr,ImGuiPopupFlags_AnyPopupId)));
 if(settings&&!TouchSettingsWasDown)Fast::Oot3d::RequestUnifiedSettingsToggle();
 TouchSettingsWasDown=settings;
}
inline void DrawTouch(bool settingsVisible) {
 if(!NativeFrontendEnabled||!TouchPlatform())return;
 NativeTouchOpacity.store(TouchOpacity);
 const int mode=settingsVisible?2:StartupVisible?1:0;
 const bool menu=mode!=0;
 TouchHudActive=TouchVisibility.ControlsVisible()&&TouchHudRequested.load()&&mode==0;
 TouchHostMenu.store(menu);TouchHostMode.store(mode);
 if(mode!=TouchMenuMode) {
  std::lock_guard lock(TouchMutex);MobileTouch.Reset();NativeTouch.Reset();TouchMenuMode=mode;
 }
 SetTouchActive(true);
 const auto* v=ImGui::GetMainViewport();
 {std::lock_guard lock(TouchMutex);MobileTouch.SetAspect(v->Size.x/std::max(v->Size.y,1.f));}
 const auto state=SampleTouch(menu);
 MenuTouchInput(state,menu,settingsVisible);
 const auto previousScale=ImGui::GetIO().FontGlobalScale;
 ImGui::GetIO().FontGlobalScale=InterfaceFontScale(InterfaceScale(v->Size.y));
#if defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
 static int nativeEnabled=-1;
 if(nativeEnabled!=static_cast<int>(TouchEnabled.load())){nativeEnabled=TouchEnabled.load();RetunedIOS_SetTouchControlsEnabled(nativeEnabled);}
 static float nativeOpacity=-1;
 if(nativeOpacity!=TouchOpacity){nativeOpacity=TouchOpacity;RetunedIOS_SetTouchOpacity(nativeOpacity);}
 static float nativeSize=-1;static int nativeFace=-1,nativeFloating=-1;
 if(nativeSize!=TouchSize.load()){nativeSize=TouchSize.load();RetunedIOS_SetTouchScale(nativeSize);}
 if(nativeFace!=TouchFaceLayout.load()){nativeFace=TouchFaceLayout.load();RetunedIOS_SetFaceButtonLayout(nativeFace);}
 if(nativeFloating!=static_cast<int>(TouchFloating.load())){nativeFloating=TouchFloating.load();RetunedIOS_SetTouchLeftStickFloating(nativeFloating);}
 static int nativeJump=-1;
 const int jump=menu?0:TouchManualJumpMode.load();
 if(nativeJump!=jump){nativeJump=jump;RetunedIOS_SetManualJump(jump);}
 static int nativeExtra=-1;
 if(nativeExtra!=static_cast<int>(TouchExtraShoulders.load())){nativeExtra=TouchExtraShoulders.load();RetunedIOS_SetExtraShoulders(nativeExtra);}
 static int nativeHud=-1;
 const bool showHudIcons=TouchHudActive.load()&&TouchHudLive.load();
 if(nativeHud!=static_cast<int>(showHudIcons)){nativeHud=showHudIcons;RetunedIOS_SetTouchHudIcons(nativeHud);}
 RetunedIOS_SetTouchControlsMenuVisible(mode);
 ImGui::GetIO().FontGlobalScale=previousScale;
 return;
#endif
#ifdef __ANDROID__
 ImGui::GetIO().FontGlobalScale=previousScale;
 return;
#endif
 auto* draw=ImGui::GetForegroundDrawList();
 for(const auto& c:TouchLayout) {
  if(!TouchVisibility.ControlsVisible())continue;
  if(menu && (c.Action==TouchAction::Look||c.Action==TouchAction::Target||c.Action==TouchAction::Shield||c.Action==TouchAction::ItemI||c.Action==TouchAction::ItemII||c.Action==TouchAction::X||c.Action==TouchAction::Y||c.Action==TouchAction::Inventory))continue;
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
   const float font=std::min(radius*.65f,20.f*InterfaceScale(v->Size.y));
   const ImVec2 size=ImGui::GetFont()->CalcTextSizeA(font,1000,0,c.Label);
   draw->AddText(ImGui::GetFont(),font,{center.x-size.x*.5f,center.y-size.y*.5f},IM_COL32(230,241,255,200),c.Label);
  }
 }
 ImGui::GetIO().FontGlobalScale=previousScale;
}
inline void DrawTouchSettings() {
 if(!TouchPlatform()){ImGui::TextWrapped("Touch controls are available on iPhone, iPad and Android.");return;}
 auto config=Ship::Context::GetRawInstance()->GetConfig();
 bool commit=false,enabled=TouchEnabled.load(),floating=TouchFloating.load();
 if(Toggle("Show touch controls",&enabled)){TouchVisibility.Configure(enabled);commit=true;}
#ifdef __ANDROID__
 if(ImGui::Button("Edit touch layout")) {
  auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());
  auto activity=static_cast<jobject>(SDL_AndroidGetActivity());
  if(env&&activity) {
   auto type=env->GetObjectClass(activity);
   auto method=env->GetMethodID(type,"retunedEditTouchLayout","()V");
   if(method)env->CallVoidMethod(activity,method);
   if(env->ExceptionCheck()){env->ExceptionClear();SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Could not open touch-layout editor");}
   env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
  }
 }
 ImGui::TextWrapped("Drag controls to reposition them. Single-screen and dual-screen layouts are saved separately. Map toggles the minimap without extra shoulder buttons.");
#endif
#if defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
 if(ImGui::Button("Edit touch layout"))RetunedIOS_EditTouchLayout();
 ImGui::TextWrapped("Drag controls to reposition them. Single-screen and dual-screen layouts are saved separately. Map toggles the minimap without extra shoulder buttons.");
#endif
 float size=TouchSize.load();
 if(ImGui::SliderFloat("Control size",&size,.75f,1.25f,"%.2fx"))TouchSize=size;
 commit|=ImGui::IsItemDeactivatedAfterEdit();
 ImGui::SliderFloat("Opacity",&TouchOpacity,.1f,.75f,"%.2f");commit|=ImGui::IsItemDeactivatedAfterEdit();
 if(Toggle("Floating movement stick",&floating)){TouchFloating=floating;commit=true;}
 int layout=TouchFaceLayout.load();
 if(ImGui::Combo("Face-button layout",&layout,"Nintendo\0Xbox\0GameCube\0")){TouchFaceLayout=layout;commit=true;}
 bool icons=TouchHudRequested.load();
 if(Toggle("Item icons on touch controls",&icons)){TouchHudRequested=icons;commit=true;}
 float iconOpacity=TouchIconOpacity.load();
 if(ImGui::SliderFloat("Item icon opacity",&iconOpacity,0.f,1.f,"%.2f"))TouchIconOpacity=iconOpacity;
 commit|=ImGui::IsItemDeactivatedAfterEdit();
 bool extras=TouchExtraShoulders.load();
 if(Toggle("Show ZL / ZR",&extras)){TouchExtraShoulders=extras;commit=true;}
 if(extras) {
  constexpr const char* labels[]={"Unassigned","A","B","X","Y","Targeting","Shield","Inventory","D-pad up","D-pad down","D-pad left","D-pad right"};
  constexpr int actions[]={-1,0,1,2,3,4,5,8,10,11,12,13};
  auto assign=[&](const char* label,std::atomic<int>& stored){
   int selected=0;for(int i=0;i<12;++i)if(actions[i]==stored.load())selected=i;
   if(ImGui::Combo(label,&selected,labels,12)){stored=actions[selected];commit=true;}
  };
  assign("ZL action",TouchZLAction);
  ImGui::BeginDisabled(TouchManualJumpMode.load()!=0);assign("ZR action",TouchZRAction);ImGui::EndDisabled();
 }
 if(TouchManualJumpMode.load()!=0)ImGui::TextWrapped(TouchManualJumpMode.load()==2?"Manual jump: X jumps; ZR uses the X item. ZR is shown automatically.":"Manual jump: ZR jumps and is shown automatically.");
 ImGui::TextWrapped("The visibility button appears only when touch controls are enabled. It temporarily hides or restores the controls without changing this setting.");
 ImGui::Spacing();ImGui::TextWrapped("L: targeting. R: shield. D-pad: item shortcuts. Start: inventory. Settings: app options.");
 if(commit){
  {std::lock_guard lock(TouchMutex);NativeTouch.Reset();}
  config->SetFloat("Touch.IconOpacity",TouchIconOpacity.load());
  config->SetBool("Touch.ItemIcons",TouchHudRequested.load());
  config->SetBool("Touch.ExtraShoulders",TouchExtraShoulders.load());config->SetInt("Touch.ZLAction",TouchZLAction.load());config->SetInt("Touch.ZRAction",TouchZRAction.load());
  config->SetBool("Touch.Enabled",TouchEnabled.load());config->SetFloat("Touch.Scale",TouchSize.load());
  config->SetFloat("Touch.Opacity",TouchOpacity);config->SetBool("Touch.Floating",TouchFloating.load());config->SetInt("Touch.FaceLayout",TouchFaceLayout.load());config->Save();
 }
}
}
