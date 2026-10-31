"""Install experimental Duo presentation into a prepared Apple host tree.

Requires the matching game-preparation capability.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'frontend'))
from apply_reframed_screen_probe import apply as apply_renderer
from apply_native_port import edit


def apply(engine):
    engine=Path(engine)
    apply_renderer(engine)
    app=engine/'ports/apple'
    for name in ('duo_layout_observer.h','duo_layout_observer.mm','duo_game_view.mm','duo_equipment_strip.h','duo_equipment_strip.mm'):
        (app/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    cmake=app/'app.cmake'
    marker='# Isolated Duo playable probe (explicit applier only).'
    text=cmake.read_text()
    if marker not in text:
        cmake.write_text(text+'\n'+marker+'''
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/duo_layout_observer.mm" "${CMAKE_CURRENT_LIST_DIR}/duo_game_view.mm")
    target_include_directories(oot3d_native_game PRIVATE "${CMAKE_SOURCE_DIR}/runtime/three_ds_recomp/include")
    set_source_files_properties("${CMAKE_CURRENT_LIST_DIR}/duo_layout_observer.mm" "${CMAKE_CURRENT_LIST_DIR}/duo_game_view.mm" PROPERTIES COMPILE_FLAGS "-fobjc-arc")
    target_link_libraries(oot3d_native_game PRIVATE "-framework QuartzCore")
endif()
''')
    text=cmake.read_text()
    if '/duo_equipment_strip.mm' not in text:
        cmake.write_text(text+'\nif(CMAKE_SYSTEM_NAME STREQUAL "iOS")\n    target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/duo_equipment_strip.mm")\n    set_source_files_properties("${CMAKE_CURRENT_LIST_DIR}/duo_equipment_strip.mm" PROPERTIES COMPILE_FLAGS "-fobjc-arc")\nendif()\n')
    inc=engine/'runtime/three_ds_recomp/include/fast/oot3d'
    runtime=engine/'tools/oot3d/native_game_runtime'
    (inc/'retuned_lower_equipment.h').write_bytes((Path(__file__).resolve().parents[2]/'frontend/lower_equipment.h').read_bytes())
    (runtime/'retuned_shared_lower_equipment_runtime.h').write_bytes((Path(__file__).resolve().parents[1]/'lower_equipment_runtime.h').read_bytes())
    (inc/'retuned_lower_resolution.h').write_bytes((Path(__file__).resolve().parents[1]/'android/dual_screen/lower_resolution.h').read_bytes())
    resolution=inc/'render_resolution_policy.h'
    edit(resolution,'#include "fast/oot3d/graphics_settings.h"','#include "fast/oot3d/graphics_settings.h"\n#include "retuned_screen_probe.h"\n#include "retuned_lower_resolution.h"')
    edit(resolution,'    RenderExtent base = guestExtent;', '    if(RetunedFrontend::DuoProbeRequested() && RetunedFrontend::ProbeGuestDualActive.load()) {\n        if(const auto lower=RetunedFrontend::AndroidLowerRenderExtent(guestExtent.Width,guestExtent.Height,\n            RetunedFrontend::LowerEquipmentSurfaceWidth.load(),RetunedFrontend::LowerEquipmentSurfaceHeight.load()))\n            return ScaleRenderExtent({lower->Width,lower->Height},internalScale);\n    }\n    RenderExtent base = guestExtent;')
    frame=runtime/'oot3d_native_a32_window_frame.cpp'
    text=frame.read_text()
    if '#include "retuned_shared_lower_equipment_runtime.h"' not in text:
        frame.write_text('#include "retuned_shared_lower_equipment_runtime.h"\n'+text)
    edit(frame,'  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(','  if(RetunedFrontend::DuoProbeRequested())\n    RetunedFrontend::UpdateLowerEquipment(process,gui->GetMenuOrMenubarVisible() || gui->GetAnyGuiWindowVisible() || RetunedFrontend::StartupVisible,RetunedFrontend::ProbeGuestDualActive.load());\n  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(')
    setup=runtime/'oot3d_native_a32_window_setup.cpp'
    edit(setup,'  context = Ship::Context::GetRawInstance();', '  context = Ship::Context::GetRawInstance();\n  if(RetunedFrontend::DuoProbeRequested()) {\n    RetunedFrontend::DuoDisplay.Select(context->GetConfig()->GetBool("Interface.DualScreen",false)?RetunedFrontend::ScreenPreference::Dual:RetunedFrontend::ScreenPreference::Single);\n    RetunedFrontend::LowerEquipmentPanelEnabled=context->GetConfig()->GetBool("Interface.DualEquipmentPanel",true);\n  }')
    graphics=engine/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    edit(graphics,'#include <algorithm>','#include <algorithm>\n#include "fast/oot3d/retuned_screen_probe.h"')
    from panel_staging import stage_platform_display_settings
    stage_platform_display_settings(engine)
    # Apple's simulator advertises a 32-byte MRT budget. The optional grass
    # initializer eagerly builds 44/52-byte pipelines even with grass disabled.
    # Keep this diagnostic on Authentic rendering; no physical-device change.
    grass=engine/'runtime/three_ds_recomp/src/fast/oot3d/interactive_grass_pass.cpp'
    text=grass.read_text()
    marker='#include <TargetConditionals.h>'
    if marker not in text:grass.write_text('#if defined(__APPLE__)\n'+marker+'\n#endif\n'+text)
    edit(grass,'''    Shutdown();
    mImpl->PhysicalDevice = physicalDevice;''','''    Shutdown();
#if defined(__APPLE__) && TARGET_OS_SIMULATOR
    mImpl->Reason = "Optional grass unavailable in the isolated Duo simulator test";
    return false;
#endif
    mImpl->PhysicalDevice = physicalDevice;''')
    main=engine/'tools/oot3d/native_game_runtime/oot3d_native_game.cpp'
    edit(main,'''        if (argc >= 2 && std::string_view(argv[1]) == "--prebuild-interior-sun")
            return Oot3dNativeGame::InteriorSunToolMain(argc, argv);''','''#if !defined(RETUNED_APPLE_MOBILE)
        if (argc >= 2 && std::string_view(argv[1]) == "--prebuild-interior-sun")
            return Oot3dNativeGame::InteriorSunToolMain(argc, argv);
#endif''')
    backend=engine/'runtime/three_ds_recomp/src/fast/backends/gfx_sdl2.cpp'
    text=backend.read_text()
    if 'extern "C" void RetunedAttachDuoGameView' not in text:
        backend.write_text('''#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif
#if defined(__IOS__) && TARGET_OS_IOS && !TARGET_OS_TV
extern "C" void RetunedAttachDuoGameView(struct SDL_Window*);
#endif
'''+text)
    edit(backend,'    Fast::GuiWindowInitData window_impl;', '''#if defined(__IOS__) && TARGET_OS_IOS && !TARGET_OS_TV
    RetunedAttachDuoGameView(mWnd);
#endif
    Fast::GuiWindowInitData window_impl;''')


if __name__=='__main__':apply(Path(sys.argv[1]))
