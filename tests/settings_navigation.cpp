#include "../tools/frontend/settings_navigation.h"
#include <cassert>
#include <initializer_list>
int main() {
 using namespace RetunedFrontend;
 for(bool television : {true,false}) {
  ImGui::CreateContext();SettingsNav={};auto& io=ImGui::GetIO();
  io.IniFilename=nullptr;io.LogFilename=nullptr;io.DisplaySize={1280,720};io.DeltaTime=1.f/60;
  io.ConfigFlags|=ImGuiConfigFlags_NavEnableKeyboard|ImGuiConfigFlags_NavEnableGamepad;
  io.BackendFlags|=ImGuiBackendFlags_HasGamepad;
  unsigned char* pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
  if(!television)ImGui::GetCurrentContext()->NavInputSource=ImGuiInputSource_Gamepad;
  int page=0;bool option=false;bool openPopup=false;ImGuiID firstID=0,secondID=0;
  auto frame=[&] {
   ImGui::NewFrame();SettingsNav.Begin(television);
   ImGui::SetNextWindowSize({900,600});ImGui::Begin("Settings");
   ImGui::BeginChild("Categories",{220,0},true);
   bool first=ImGui::Button("General",{180,60});firstID=ImGui::GetItemID();
   if(first){page=0;SettingsNav.ActivateCategory(firstID);}
   bool second=ImGui::Button("Graphics",{180,60});secondID=ImGui::GetItemID();
   if(second){page=1;SettingsNav.ActivateCategory(secondID);}
   SettingsNav.SelectedCategory=page==0?firstID:secondID;
   SettingsNav.CategoriesDrawn(30+page*65);
   ImGui::EndChild();ImGui::SameLine();
   ImGui::BeginChild("Page",{0,0},true);SettingsNav.PageBegun();
   ImGui::TextUnformatted("Non-interactive heading");
   if(page==0)ImGui::Checkbox("First option",&option);
   else ImGui::Checkbox("Graphics option",&option);
   if(openPopup){ImGui::OpenPopup("Test choice");openPopup=false;}
   if(ImGui::BeginPopup("Test choice")){ImGui::Selectable("Choice");ImGui::EndPopup();}
   ImGui::EndChild();ImGui::End();SettingsNav.End();ImGui::Render();
  };
  auto key=[&](ImGuiKey k){io.AddKeyEvent(k,true);frame();io.AddKeyEvent(k,false);frame();frame();};
  frame();frame();
  assert(SettingsNav.LastPane==SettingsNavigation::Pane::Categories);
  key(television?ImGuiKey_RightArrow:ImGuiKey_GamepadDpadRight);
  assert(SettingsNav.LastPane==SettingsNavigation::Pane::Page);
  assert(ImGui::GetCurrentContext()->NavId!=0);
  key(television?ImGuiKey_Enter:ImGuiKey_GamepadFaceDown);
  assert(option);
  openPopup=true;frame();frame();
  assert(SettingsNav.HadPopup);
  key(television?ImGuiKey_Escape:ImGuiKey_GamepadFaceRight);
  assert(!SettingsNav.HadPopup && !SettingsNav.Close);
  assert(SettingsNav.LastPane==SettingsNavigation::Pane::Page);
  key(television?ImGuiKey_Escape:ImGuiKey_GamepadFaceRight);
  assert(SettingsNav.LastPane==SettingsNavigation::Pane::Categories && !SettingsNav.Close);
  assert(ImGui::GetCurrentContext()->NavId==firstID);
  key(television?ImGuiKey_DownArrow:ImGuiKey_GamepadDpadDown);
  key(television?ImGuiKey_Enter:ImGuiKey_GamepadFaceDown);
  assert(page==1 && SettingsNav.LastPane==SettingsNavigation::Pane::Page);
  key(television?ImGuiKey_LeftArrow:ImGuiKey_GamepadDpadLeft);
  assert(SettingsNav.LastPane==SettingsNavigation::Pane::Categories);
  assert(ImGui::GetCurrentContext()->NavId==secondID);
  io.AddKeyEvent(television?ImGuiKey_Escape:ImGuiKey_GamepadFaceRight,true);frame();
  assert(SettingsNav.Close);
  ImGui::DestroyContext();
 }
}
