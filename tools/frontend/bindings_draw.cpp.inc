  void DrawBindings() {
    const float f=ImGui::GetFontSize();
    if(RetunedFrontend::MobileSettingsPlatform())mBindingDevice=BindingDevice::Controller;
    for(const auto& [label,device]:std::array{std::pair{"Controller",BindingDevice::Controller},std::pair{"Keyboard",BindingDevice::Keyboard},std::pair{"Mouse",BindingDevice::Mouse}}) {
      if(RetunedFrontend::MobileSettingsPlatform() && device!=BindingDevice::Controller)continue;
      if(device!=BindingDevice::Controller)ImGui::SameLine();
      const bool selected=mBindingDevice==device;
      if(selected)ImGui::PushStyleColor(ImGuiCol_Button,ImGui::GetStyleColorVec4(ImGuiCol_Header));
      if(ImGui::Button(label,ImVec2(f*6.2f,0)))mBindingDevice=device;
      if(selected)ImGui::PopStyleColor();
    }
    ImGui::Spacing();ImGui::SetNextItemWidth(std::min(ImGui::GetContentRegionAvail().x,f*36));
    if(!RetunedFrontend::TelevisionPlatform())ImGui::InputTextWithHint("##ActionFilter","Find a control",mActionFilter.data(),mActionFilter.size());
    ImGui::PushID(static_cast<int>(mBindingDevice));
    bool any=false;
    for(const auto groupIndex:{1,2,3,0,4}) {
      const auto& group=kBindingGroups[groupIndex];bool matches=false;
      for(auto i=group.First;i<group.End;++i)matches|=ControlWidgets::Contains(kActionLabels[i],mActionFilter.data());
      if(matches){DrawBindingGroup(group);any=true;}
    }
    if(!any)ImGui::TextDisabled("No matching controls");
    ImGui::PopID();
  }
