"""Keep tvOS navigation independent of gameplay mappings and hide desktop-only choices."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
    engine=Path(engine)
    gui=engine/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    edit(gui,'            ImGui_ImplSDL2_NewFrame();', '''            if(RetunedFrontend::NativeFrontendEnabled)
                RetunedFrontend::EnableMenuNavigation(RetunedFrontend::TelevisionPlatform());
            ImGui_ImplSDL2_NewFrame();''')
    edit(gui,'            ImGui_ImplSDL2_InitForVulkan(static_cast<SDL_Window*>(mImpl.Vulkan.Window));', '''            ImGui_ImplSDL2_InitForVulkan(static_cast<SDL_Window*>(mImpl.Vulkan.Window));
            if(RetunedFrontend::TelevisionPlatform())ImGui_ImplSDL2_SetGamepadMode(ImGui_ImplSDL2_GamepadMode_AutoAll);''')
    anchor='            switch (sdlEvent.type) {'
    text=gui.read_text()
    begin=text.find('            if(RetunedFrontend::TelevisionPlatform() && RetunedFrontend::NativeFrontendEnabled &&')
    if begin>=0:
        end=text.index(anchor,begin)
        gui.write_text(text[:begin]+text[end:])
    edit(gui,anchor,'''            if(RetunedFrontend::TelevisionPlatform() && RetunedFrontend::NativeFrontendEnabled &&
               (sdlEvent.type==SDL_KEYDOWN || sdlEvent.type==SDL_KEYUP) && sdlEvent.key.keysym.scancode==SDL_SCANCODE_ESCAPE) {
                if(!ImGui::IsPopupOpen(nullptr,ImGuiPopupFlags_AnyPopupId|ImGuiPopupFlags_AnyPopupLevel) && !ImGui::IsAnyItemActive()) {
                    if(sdlEvent.type==SDL_KEYDOWN && !sdlEvent.key.repeat &&
                       RetunedFrontend::RemoteBackTogglesSettings(RetunedFrontend::StartupVisible,GetAnyGuiWindowVisible(),false,false))ToggleOot3dGraphicsWindow();
                    break;
                }
            }
'''+anchor)
    text=gui.read_text()
    before='    ImGui::Begin("Main Game", nullptr, flags);'
    after='    if(RetunedFrontend::NativeFrontendEnabled)flags=RetunedFrontend::GameCanvasFlags(flags);\n'+before
    if after not in text:
        assert text.count(before)==2
        gui.write_text(text.replace(before,after))
    core=engine/'runtime/three_ds_recomp/src/ship/window/gui/Gui.cpp'
    text=core.read_text()
    if '(!RetunedFrontend::TelevisionPlatform() && ImGui::IsKeyPressed(ImGuiKey_Escape, false))' not in text:
        core.write_text(text.replace('ImGui::IsKeyPressed(ImGuiKey_Escape, false)', '(!RetunedFrontend::TelevisionPlatform() && ImGui::IsKeyPressed(ImGuiKey_Escape, false))'))
    controls=engine/'tools/oot3d/native_game_runtime/oot3d_native_controls_settings_panel.cpp'
    edit(controls,'#include <utility>','#include <utility>\n#include <type_traits>')
    # Preserve existing values for visibility, but offer applicable presets and inputs.
    edit(controls,'      const auto option = ControlWidgets::DisplayName(name(values[index]));', '''      if(RetunedFrontend::TelevisionPlatform() && values[index]!=*value) {
        if constexpr(std::is_same_v<Enum,NativeControlProfile>) {
          if(values[index]!=NativeControlProfile::Controller)continue;
        }
        if constexpr(std::is_same_v<Enum,NativeMotionSource>) {
          if(values[index]==NativeMotionSource::Mouse)continue;
        }
      }
      const auto option = ControlWidgets::DisplayName(name(values[index]));''')
    edit(controls,'    if (SourceUses(mControlDraft.NativeAimSource,\n                   NativeMotionSource::Mouse)) {',
         '    if (!RetunedFrontend::TelevisionPlatform() && SourceUses(mControlDraft.NativeAimSource,\n                   NativeMotionSource::Mouse)) {')
    edit(controls,'    if (SourceUses(mControlDraft.FreeCameraSource,\n                   NativeMotionSource::Mouse)) {',
         '    if (!RetunedFrontend::TelevisionPlatform() && SourceUses(mControlDraft.FreeCameraSource,\n                   NativeMotionSource::Mouse)) {')
