  void DrawBindingGroup(const BindingGroup& group) {
    ImGui::PushID(group.Name);
    ImGui::Spacing();ImGui::SeparatorText(group.Name);
    const float f=ImGui::GetFontSize();
    const float width=std::min(ImGui::GetContentRegionAvail().x,f*36);
    if(ImGui::BeginTable("##BindingRows",2,ImGuiTableFlags_SizingStretchProp|ImGuiTableFlags_NoSavedSettings,ImVec2(width,0))) {
      ImGui::TableSetupColumn("Action",ImGuiTableColumnFlags_WidthStretch,1.0f);
      ImGui::TableSetupColumn("Binding",ImGuiTableColumnFlags_WidthStretch,1.25f);
      for(size_t index=group.First;index<group.End;++index) {
        if(!ControlWidgets::Contains(kActionLabels[index],mActionFilter.data()))continue;
        auto& binding=mControlDraft.Bindings[index];
        ImGui::PushID(static_cast<int>(index));ImGui::TableNextRow(0,f*2.4f);
        ImGui::TableSetColumnIndex(0);ImGui::AlignTextToFramePadding();ImGui::TextUnformatted(kActionLabels[index]);
        ImGui::TableSetColumnIndex(1);
        const char* name=mBindingDevice==BindingDevice::Keyboard?NativeKeyboardKeyName(binding.KeyboardPrimary):
            mBindingDevice==BindingDevice::Mouse?NativeMouseButtonName(binding.Mouse):NativeGamepadButtonName(binding.Gamepad);
        const auto display=ControlWidgets::DisplayName(name);
        const float available=ImGui::GetContentRegionAvail().x;
        if(ImGui::Button((display+"##Assign").c_str(),ImVec2(std::max(f*4,available-f*3),0)))
          BeginBindingCapture(index,mBindingDevice==BindingDevice::Keyboard?BindingSlot::Primary:mBindingDevice==BindingDevice::Mouse?BindingSlot::Mouse:BindingSlot::Gamepad);
        ImGui::SameLine();
        if(ImGui::Button("X##Clear",ImVec2(f*2,0))) {
          if(mBindingDevice==BindingDevice::Keyboard){binding.KeyboardPrimary=NativeKeyboardKey::None;binding.KeyboardSecondary=NativeKeyboardKey::None;}
          else if(mBindingDevice==BindingDevice::Mouse)binding.Mouse=NativeMouseButton::None;
          else binding.Gamepad=NativeGamepadButton::None;
          MarkCustom(mControlDraft,mControlDirty);
        }
        if(ImGui::IsItemHovered())ImGui::SetTooltip("Clear this binding");
        if(mBindingDevice==BindingDevice::Keyboard) {
          const auto alternate=ControlWidgets::DisplayName(NativeKeyboardKeyName(binding.KeyboardSecondary));
          if(ImGui::SmallButton(("Alternate: "+alternate+"##Alt").c_str()))BeginBindingCapture(index,BindingSlot::Alternate);
        }
        ImGui::PopID();
      }
      ImGui::EndTable();
    }
    ImGui::PopID();
  }
