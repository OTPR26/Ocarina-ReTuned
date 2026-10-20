#import <GameController/GameController.h>
#include <imgui.h>
#include "fast/oot3d/retuned_television_remote.h"
#include "fast/oot3d/graphics_settings_window.h"
namespace {
void NativeMenuGamepadFallback() {
 auto& io=ImGui::GetIO();
 if(io.BackendFlags&ImGuiBackendFlags_HasGamepad)return;
 bool found=false;bool up=false,down=false,left=false,right=false,a=false,b=false,x=false,y=false;
 for(GCController* controller in GCController.controllers) {
  GCExtendedGamepad* pad=controller.extendedGamepad;if(!pad)continue;
  found=true;up|=pad.dpad.up.isPressed||pad.leftThumbstick.yAxis.value>.5f;
  down|=pad.dpad.down.isPressed||pad.leftThumbstick.yAxis.value<-.5f;
  left|=pad.dpad.left.isPressed||pad.leftThumbstick.xAxis.value<-.5f;
  right|=pad.dpad.right.isPressed||pad.leftThumbstick.xAxis.value>.5f;
  a|=pad.buttonA.isPressed;b|=pad.buttonB.isPressed;x|=pad.buttonX.isPressed;y|=pad.buttonY.isPressed;
 }
 if(found)io.BackendFlags|=ImGuiBackendFlags_HasGamepad;
 io.AddKeyEvent(ImGuiKey_GamepadDpadUp,up);io.AddKeyEvent(ImGuiKey_GamepadDpadDown,down);
 io.AddKeyEvent(ImGuiKey_GamepadDpadLeft,left);io.AddKeyEvent(ImGuiKey_GamepadDpadRight,right);
 io.AddKeyEvent(ImGuiKey_GamepadFaceDown,a);io.AddKeyEvent(ImGuiKey_GamepadFaceRight,b);
 io.AddKeyEvent(ImGuiKey_GamepadFaceLeft,x);io.AddKeyEvent(ImGuiKey_GamepadFaceUp,y);
}
}
extern "C" void RetunedTVUpdateRemote(bool startup,bool settings) {
 using namespace RetunedFrontend;
 if(startup||settings)NativeMenuGamepadFallback();
 TelevisionRemoteButtons input{};
 for(GCController* controller in GCController.controllers) {
  // Extended controllers continue through SDL; the remote owns a separate menu path.
  if(controller.extendedGamepad || !controller.microGamepad)continue;
  GCMicroGamepad* remote=controller.microGamepad;
  remote.allowsRotation=NO;remote.reportsAbsoluteDpadValues=YES;
  const auto buttons=RemoteButtons(remote.dpad.xAxis.value,remote.dpad.yAxis.value,
                                   remote.buttonA.isPressed,remote.buttonMenu.isPressed);
  input.Up|=buttons.Up;input.Down|=buttons.Down;input.Left|=buttons.Left;input.Right|=buttons.Right;
  input.Accept|=buttons.Accept;input.Back|=buttons.Back;
 }
 static bool backHeld=false,suppressOpeningBack=false;
 if(!input.Back)suppressOpeningBack=false;
 if(!startup&&!settings&&input.Back&&!backHeld){
  Fast::Oot3d::RequestUnifiedSettingsToggle();suppressOpeningBack=true;
 }
 backHeld=input.Back;
 auto& io=ImGui::GetIO();
 const bool menu=startup||settings;
 io.AddKeyEvent(ImGuiKey_UpArrow,menu&&input.Up);io.AddKeyEvent(ImGuiKey_DownArrow,menu&&input.Down);
 io.AddKeyEvent(ImGuiKey_LeftArrow,menu&&input.Left);io.AddKeyEvent(ImGuiKey_RightArrow,menu&&input.Right);
 io.AddKeyEvent(ImGuiKey_Enter,menu&&input.Accept);io.AddKeyEvent(ImGuiKey_Escape,menu&&input.Back&&!suppressOpeningBack);
}
