// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_cheats.h"
#include "ship/Context.h"
#include "ship/config/Config.h"
#include <imgui.h>
namespace RetunedFrontend {
inline void DrawCheats() {
 auto config=Ship::Context::GetRawInstance()->GetConfig();
 std::lock_guard lock(Cheats.Mutex);
 auto options=Cheats.Options;
 bool changed=false;
 changed|=ImGui::Checkbox("Infinite health",&options.Health);
 if(ImGui::GetContentRegionAvail().x>ImGui::GetFontSize()*26)ImGui::SameLine();
 changed|=ImGui::Checkbox("Infinite magic",&options.Magic);
 ImGui::TextWrapped("Uses your acquired items and current capacities.");
 ImGui::SeparatorText("Amounts");
 const auto& state=Cheats.Snapshot;
 static CheatSnapshot draft;static bool initialized=false;
 if(!state.Ready)initialized=false;
 if(state.Ready&&(!initialized||draft.Save!=state.Save||draft.File!=state.File||draft.Entrance!=state.Entrance)){
  draft=state;initialized=true;
 }
 ImGui::BeginDisabled(!state.Ready||Cheats.Edit.Pending);
 if(ImGui::Button("Refresh amounts"))draft=state;
 ImGui::EndDisabled();
 auto row=[&](const char* name,int& amount,int current,int maximum,bool& infinite){
  ImGui::PushID(name);
  ImGui::TextUnformatted(name);
  const float toggleWidth=ImGui::GetFrameHeight()+ImGui::CalcTextSize("Infinite").x+ImGui::GetStyle().ItemInnerSpacing.x;
  const float available=ImGui::GetContentRegionAvail().x-toggleWidth-ImGui::GetStyle().ItemSpacing.x;
  ImGui::SetNextItemWidth(std::max(1.f,std::min(available,ImGui::GetFontSize()*18.f)));
  int displayed=infinite?maximum:std::clamp(amount,0,maximum);
  ImGui::BeginDisabled(!state.Ready||Cheats.Edit.Pending||infinite||maximum==0);
  if(ImGui::SliderInt("##amount",&displayed,0,maximum))amount=displayed;
  ImGui::EndDisabled();
  ImGui::SameLine();
  if(ImGui::Checkbox("Infinite",&infinite)){
   changed=true;
   if(!infinite)amount=std::clamp(current,0,maximum);
  }
  ImGui::PopID();
 };
 row("Rupees",draft.Rupees,state.Rupees,state.Wallet,options.Rupees);
 for(unsigned i=0;i<CheatAmmunition.size();++i)
  if(!state.Ready||state.Capacity[i]>0)
   row(CheatAmmunition[i].Name,draft.Ammo[i],state.Ammo[i],state.Capacity[i],options.Ammo[i]);
 if(changed){
  if(config->SetBlock("Cheats",nlohmann::json{{"health",options.Health},{"magic",options.Magic},{"ammo",options.Ammo},{"rupees",options.Rupees}}))
   Cheats.Options=options;
  else Cheats.Message="Could not save cheat settings. Your previous settings remain active.";
 }
 bool editable=!Cheats.Options.Rupees;
 for(unsigned i=0;i<CheatAmmunition.size();++i)editable|=state.Capacity[i]>0&&!Cheats.Options.Ammo[i];
 ImGui::BeginDisabled(!state.Ready||Cheats.Edit.Pending||!editable);
 if(ImGui::Button("Apply")){
  CheatEdit edit;edit.Pending=true;edit.Origin=draft;
  if(!Cheats.Options.Rupees)edit.Rupees=std::clamp(draft.Rupees,0,state.Wallet);
  for(unsigned i=0;i<CheatAmmunition.size();++i)
   if(state.Capacity[i]>0&&!Cheats.Options.Ammo[i])edit.Ammo[i]=std::clamp(draft.Ammo[i],0,state.Capacity[i]);
  Cheats.Edit=edit;Cheats.Message="Return to gameplay to apply changes.";
 }
 ImGui::EndDisabled();
 if(!state.Ready)ImGui::TextWrapped("Load a save to see your amounts and capacities.");
 ImGui::TextWrapped("Infinite locks that amount at your current maximum. Manual changes are retained when you save in game.");
 if(!Cheats.Message.empty())ImGui::TextWrapped("%s",Cheats.Message.c_str());
}
}
