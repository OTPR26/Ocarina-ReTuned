// SPDX-License-Identifier: GPL-2.0-or-later
#include "../tools/frontend/menu_navigation.h"
#include <imgui_internal.h>
#include <cassert>
#include <initializer_list>
int main() {
 for(bool gameplayScoped:{false,true}) {
  auto* context=ImGui::CreateContext();auto& io=ImGui::GetIO();
  io.IniFilename=nullptr;io.LogFilename=nullptr;io.DisplaySize={1920,1080};io.DeltaTime=1.f/60;
  io.BackendFlags|=ImGuiBackendFlags_HasGamepad;
  unsigned char* pixels;int width,height;io.Fonts->GetTexDataAsRGBA32(&pixels,&width,&height);
  auto frame=[&] {
   RetunedFrontend::SetMenuNavigationActive(!gameplayScoped);
   ImGui::NewFrame();ImGui::Begin("Canvas host");ImGui::End();ImGui::Render();
  };
  frame();frame();io.AddKeyEvent(ImGuiKey_GamepadFaceLeft,true);
  for(int i=0;i<60;++i)frame();
  // Reproduce the original X/Square window-switch overlay; the scoped
  // gameplay policy prevents it even if a backend canvas remains focusable.
  assert((context->NavWindowingTarget!=nullptr)==!gameplayScoped);
  if(!gameplayScoped) {
   auto* overlay=ImGui::FindWindowByName("##NavWindowingOverlay");assert(overlay);
   assert(overlay->Size.x>=io.DisplaySize.x*.2f&&overlay->Size.y>=io.DisplaySize.y*.2f);
  }
  if(!gameplayScoped) {
   // Return to gameplay with the menu shortcut still held. Merely clearing
   // NavEnableGamepad leaves the target and fade alive in Dear ImGui.
   RetunedFrontend::SetMenuNavigationActive(false);
   assert(!context->NavWindowingTarget&&!context->NavWindowingTargetAnim);
   assert(context->NavWindowingHighlightAlpha==0&&!context->NavWindowingToggleLayer);
   for(int frameIndex=0;frameIndex<60;++frameIndex) {
    RetunedFrontend::SetMenuNavigationActive(false);
    ImGui::NewFrame();ImGui::Begin("Canvas host");ImGui::End();ImGui::Render();
    assert(!context->NavWindowingTarget&&!context->NavWindowingTargetAnim);
    auto* overlay=ImGui::FindWindowByName("##NavWindowingOverlay");
    assert(!overlay||!overlay->Active);
   }
  }
  io.AddKeyEvent(ImGuiKey_GamepadFaceLeft,false);frame();
  RetunedFrontend::SetMenuNavigationActive(true);
  assert(io.ConfigFlags&ImGuiConfigFlags_NavEnableGamepad);
  assert(io.ConfigFlags&ImGuiConfigFlags_NavEnableKeyboard);
  ImGui::DestroyContext();
 }
}
