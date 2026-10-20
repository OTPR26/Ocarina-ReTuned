#include "../tools/frontend/blue_style.h"
#include <cassert>
#include "../tools/frontend/menu_navigation.h"
int main() {
 for(bool canvasProtected : {false,true}) {
 ImGui::CreateContext();auto& io=ImGui::GetIO();io.IniFilename=nullptr;io.LogFilename=nullptr;
 io.DisplaySize={1280,720};io.DeltaTime=1.f/60;
 RetunedFrontend::EnableMenuNavigation(true);
 io.BackendFlags|=ImGuiBackendFlags_HasGamepad;
 unsigned char* pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
 bool first=false,second=false;
 auto frame=[&] {
  ImGui::NewFrame();ImGui::SetNextWindowSize({600,500});ImGui::Begin("Settings");
  RetunedFrontend::Toggle("First option",&first);
  if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
  RetunedFrontend::Toggle("Second option",&second);
  ImGui::End();
  // The renderer submits its empty canvas after the menu. It must not steal focus.
  ImGui::Begin("Main Game",nullptr,canvasProtected?RetunedFrontend::GameCanvasFlags(ImGuiWindowFlags_NoTitleBar):ImGuiWindowFlags_NoTitleBar);
  ImGui::End();ImGui::Render();
 };
 frame();frame();
 // Remote click is Enter; the paired controller uses its primary face button.
 io.AddKeyEvent(ImGuiKey_Enter,true);frame();io.AddKeyEvent(ImGuiKey_Enter,false);frame();
 if(!canvasProtected){assert(!first && !second);ImGui::DestroyContext();continue;}
 assert(first && !second);
 io.AddKeyEvent(ImGuiKey_DownArrow,true);frame();io.AddKeyEvent(ImGuiKey_DownArrow,false);frame();frame();
 io.AddKeyEvent(ImGuiKey_Enter,true);frame();io.AddKeyEvent(ImGuiKey_Enter,false);frame();
 assert(first && second);
 io.AddKeyEvent(ImGuiKey_GamepadFaceDown,true);frame();io.AddKeyEvent(ImGuiKey_GamepadFaceDown,false);frame();
 assert(first && !second);
 assert(RetunedFrontend::MenuBackClosesSettings(true,false,false,false));
 assert(!RetunedFrontend::MenuBackClosesSettings(true,true,false,false)); // Closing a popup is one Back step.
 assert(!RetunedFrontend::MenuBackClosesSettings(true,false,true,false)); // Stop editing before leaving.
 assert(!RetunedFrontend::RemoteBackTogglesSettings(true,false,false,false));
 assert(RetunedFrontend::RemoteBackTogglesSettings(false,false,false,false));
 assert(RetunedFrontend::RemoteBackTogglesSettings(true,true,false,false));
 assert(!RetunedFrontend::RemoteBackTogglesSettings(false,true,true,false));
 ImGui::DestroyContext();
 }
}
