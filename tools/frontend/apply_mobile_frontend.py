"""Shared startup, responsive settings and mobile touch layer for the native host."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
    from apply_gui_textures import apply as apply_gui_textures
    apply_gui_textures(engine)
    from apply_mobile_lifecycle import apply as apply_lifecycle
    apply_lifecycle(engine)
    from apply_mobile_settings import apply as apply_settings
    apply_settings(engine)
    from apply_touch_hud import apply as apply_touch_hud
    apply_touch_hud(engine)
    engine=Path(engine);source=Path(__file__).parent
    include=engine/'runtime/three_ds_recomp/include/fast/oot3d'
    runtime=engine/'tools/oot3d/native_game_runtime'
    android=engine/'ports/android/runtime'
    if(android.exists()):
        native=source.parents[0]/'native/apple'
        (android/'texture_folder_jni.h').write_text((source.parents[0]/'native/android/texture_folder_jni.h').read_text())
        for name in ('touch_input.cpp','touch_input_api.h'):
            (android/name).write_text((native/name).read_text())
        cmake=android/'CMakeLists.txt'
        marker='target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/touch_input.cpp")'
        if marker not in cmake.read_text():cmake.write_text(cmake.read_text()+'\n'+marker+'\n')

    for name in ('texture_folder.h','settings_pages.h','frontend_state.h','interface_metrics.h','responsive_layout.h','touch_model.h','touch_hud_model.h','touch_hud_state.h','touch_overlay.h','startup_draw.h','startup_layout.h','menu_navigation.h','television_remote.h'):
        (include/('retuned_'+name)).write_text((source/name).read_text().replace('#include "interface_metrics.h"','#include "retuned_interface_metrics.h"').replace('#include "touch_hud_model.h"','#include "retuned_touch_hud_model.h"'))
    artwork=(source.parents[1]/'resources/artwork/ocarina-illustration.png').read_bytes()
    (include/'retuned_artwork.h').write_text('#pragma once\nnamespace RetunedFrontend { inline constexpr unsigned char OcarinaArtwork[] = {\n'+','.join(map(str,artwork))+'\n}; }\n')
    gui=engine/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    # Adjacent shared patches may insert headers at the same anchor.
    for path in (gui, runtime/'oot3d_native_a32_window_setup.cpp', runtime/'oot3d_native_a32_window_frame.cpp'):
        seen=set();lines=[]
        for line in path.read_text().splitlines(keepends=True):
            if line.startswith('#include ') and 'retuned_' in line:
                if line in seen:continue
                seen.add(line)
            lines.append(line)
        path.write_text(''.join(lines))

    edit(gui,'#include "fast/oot3d/retuned_blue_style.h"','#include "fast/oot3d/retuned_blue_style.h"\n#include "fast/oot3d/retuned_touch_overlay.h"\n#include "fast/oot3d/retuned_startup_draw.h"')
    if 'RetunedFrontend::DrawStartup(*this,' not in gui.read_text():
        edit(gui,'void Fast3dGui::DrawMenu() {\n    Ship::Gui::DrawMenu();',
             'void Fast3dGui::DrawMenu() {\n    Ship::Gui::DrawMenu();\n    if(RetunedFrontend::NativeFrontendEnabled) {\n        ImGui::GetIO().ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard | ImGuiConfigFlags_NavEnableGamepad;\n        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());\n        RetunedFrontend::DrawTouch(GetAnyGuiWindowVisible());\n    }')
    edit(gui,'void Fast3dGui::DrawGame() {','void Fast3dGui::DrawGame() {\n    if(RetunedFrontend::NativeFrontendEnabled && RetunedFrontend::StartupVisible)return;')
    edit(gui,'    mImpl = windowImpl;', '    mImpl = windowImpl;\n#ifdef ENABLE_OOT3D_VULKAN\n    if (mImpl.Backend == WindowBackend::FAST3D_SDL_OOT3D_VULKAN) {\n        auto* window=static_cast<SDL_Window*>(mImpl.Vulkan.Window);\n        int width=0,height=0,pixelWidth=0,pixelHeight=0;\n        SDL_GetWindowSize(window,&width,&height);\n        SDL_Vulkan_GetDrawableSize(window,&pixelWidth,&pixelHeight);\n        RetunedFrontend::SetInterfacePixelRatio(static_cast<float>(width),static_cast<float>(pixelWidth));\n    }\n#endif')
    edit(gui,'#include "fast/Fast3dGui.h"','#include "fast/Fast3dGui.h"\n#include <SDL_vulkan.h>')
    core=engine/'runtime/three_ds_recomp/src/ship/window/gui/Gui.cpp'
    edit(core,'    // Scale everything by 2 for Android\n    ImGui::GetStyle().ScaleAllSizes(2.0f);\n    mImGuiIo->FontGlobalScale = 2.0f;',
         '    // The shared frontend derives logical scale from the current viewport.\n    mImGuiIo->FontGlobalScale = RetunedFrontend::InterfaceFontScale();')
    edit(core,'#include "fast/oot3d/retuned_interface_font.h"','#include "fast/oot3d/retuned_interface_font.h"\n#include "fast/oot3d/retuned_interface_metrics.h"')
    edit(core,'sizeof(RetunedFrontend::InterfaceFont),40.f,&interfaceFont','sizeof(RetunedFrontend::InterfaceFont),RetunedFrontend::InterfaceFontPixels(),&interfaceFont')
    edit(core,'    mImGuiIo->FontGlobalScale=.5f;','    mImGuiIo->FontGlobalScale=RetunedFrontend::InterfaceFontScale();')
    edit(core,'    float baseFontSize = 40.0f;','    float baseFontSize = RetunedFrontend::InterfaceFontPixels();')
    setup=runtime/'oot3d_native_a32_window_setup.cpp'
    edit(setup,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "fast/oot3d/retuned_touch_overlay.h"')
    edit(setup,'RetunedFrontend::Current().Initialize(launch.A32ProcessManifestPath);',
         'RetunedFrontend::Current().Initialize(launch.A32ProcessManifestPath);\n  if(launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed) {\n    RetunedFrontend::NativeFrontendEnabled=true;\n    RetunedFrontend::StartupVisible=true;\n    RetunedFrontend::InitializeTouch();\n  }')
    edit(setup,'    RetunedFrontend::NativeFrontendEnabled=true;',
         '    RetunedFrontend::GameFilesReady=true;\n    RetunedFrontend::NativeFrontendEnabled=true;')
    frame=runtime/'oot3d_native_a32_window_frame.cpp'
    edit(frame,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "fast/oot3d/retuned_frontend_state.h"')
    edit(frame,'      gui->GetMenuOrMenubarVisible() || gui->GetAnyGuiWindowVisible();',
         '      gui->GetMenuOrMenubarVisible() || gui->GetAnyGuiWindowVisible() ||\n      (RetunedFrontend::NativeFrontendEnabled && RetunedFrontend::StartupVisible);')
    before='  const auto preparationStatus = programPreparation != nullptr'
    hold='''  if(RetunedFrontend::NativeFrontendEnabled && RetunedFrontend::StartupVisible) {
    if(!presentationScheduler.Restore(presentationStateBeforeFrame,&error))
      throw std::runtime_error("cannot hold startup presentation clock: "+error);
    gui->EndDraw();
    renderStream.Submit([&] { window.EndFrame(); },true);
    std::this_thread::sleep_for(std::chrono::milliseconds(15));
    renderStream.Submit([&] { realtimePacer.ResetDeadline(); });
    lastPresentationTime=std::chrono::steady_clock::now();
    lastCompletedFrameTime=lastPresentationTime;
    return true;
  }
'''
    edit(frame,before,hold+before)
    inputs=runtime/'oot3d_native_a32_window_input.cpp'
    edit(inputs,'#include "oot3d_native_a32_window_shared.h"','#include "oot3d_native_a32_window_shared.h"\n#include "fast/oot3d/retuned_touch_overlay.h"')
    edit(inputs,'  auto frame = MapNativeControlInput(config, host, aimTransform,',(source/'touch_input.cpp.inc').read_text()+'\n  auto frame = MapNativeControlInput(config, host, aimTransform,')
    edit(inputs,'  ApplyNativeControlShortcutTouch(host, frame);','  if(RetunedFrontend::SampleTouch(false).Captured)frame.Hid.TouchPressed=false;\n  ApplyNativeControlShortcutTouch(host, frame);')
    edit(gui,'                    const int buttonIndex =\n                        Oot3dMouseButtonIndex(sdlEvent.button.button);',
         '                    if(sdlEvent.button.which==SDL_TOUCH_MOUSEID && RetunedFrontend::SampleTouch(false).Captured)break;\n                    const int buttonIndex =\n                        Oot3dMouseButtonIndex(sdlEvent.button.button);')
    graphics=engine/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    edit(graphics,'#include "fast/oot3d/retuned_blue_style.h"','#include "fast/oot3d/retuned_blue_style.h"\n#include "fast/oot3d/retuned_responsive_layout.h"\n#include "fast/oot3d/retuned_touch_overlay.h"')
    from apply_television_menu import apply as apply_television
    apply_television(engine)
    # Shared patches can insert adjacent includes at the same anchor. Keep the
    # final translation units stable when preparing a cached engine repeatedly.
    for path in (gui, setup, frame, inputs, graphics):
        seen=set();lines=[]
        for line in path.read_text().splitlines(keepends=True):
            if line.startswith('#include ') and 'retuned_' in line:
                if line in seen:continue
                seen.add(line)
            lines.append(line)
        path.write_text(''.join(lines))
