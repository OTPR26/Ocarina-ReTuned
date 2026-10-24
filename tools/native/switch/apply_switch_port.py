#!/usr/bin/env python3
"""Apply Switch-specific integration to an already prepared ReTuned engine."""
from pathlib import Path
import argparse
import sys


def write_if_changed(path, text):
    if path.read_text() != text:
        path.write_text(text)


def apply(engine):
    engine = Path(engine)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from apply_neutral_shaders import apply as apply_neutral_shaders
    apply_neutral_shaders(engine)
    from rendering import apply_rendering, apply_exclude_scissor
    apply_rendering(engine)
    apply_exclude_scissor(engine)
    from shader_cache import apply as apply_shader_cache
    apply_shader_cache(engine)
    gui = engine / 'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    text = gui.read_text()
    marker = '// ReTuned frontend is shared with the Switch OpenGL backend.'
    if marker not in text:
        headers = ('graphics_settings_runtime.h', 'graphics_settings_window.h',
                   'retuned_blue_style.h', 'retuned_touch_overlay.h',
                   'retuned_startup_draw.h', 'retuned_tab_hints.h')
        text = text.replace('#include <SDL_vulkan.h>', '#include <SDL_vulkan.h>\n' + marker +
            '\n#if defined(__SWITCH__)\n' + ''.join(
                '#include "fast/oot3d/' + name + '"\n' for name in headers) + '#endif')
        write_if_changed(gui, text)
    dlss_header = engine / 'runtime/three_ds_recomp/include/fast/oot3d/dlss_module_loader.h'
    text = dlss_header.read_text()
    if 'struct TriaevumDlssModule;' not in text:
        text = text.replace('#include "triaevum/dlss_module.h"',
        '#if defined(__SWITCH__)\nstruct TriaevumDlssModule;\n#else\n#include "triaevum/dlss_module.h"\n#endif')
    write_if_changed(dlss_header, text)
    dlss = engine / 'runtime/three_ds_recomp/src/fast/oot3d/dlss_module_loader.cpp'
    text = dlss.read_text()
    if not text.startswith('#if defined(__SWITCH__)'):
        dlss.write_text('#if defined(__SWITCH__)\n#include "fast/oot3d/dlss_module_loader.h"\n'
            'namespace Fast::Oot3d {\nconst TriaevumDlssModule* DlssModule() { return nullptr; }\n'
            'const std::string& DlssModuleUnavailableReason() {\n'
            'static const std::string reason="DLSS is unavailable on Switch"; return reason; }\n}\n'
            '#else\n' + text + '\n#endif\n')
    panel = engine / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_antialiasing_panel.cpp'
    text = panel.read_text()
    attribution = ('            if (const auto* module = DlssModule(); module != nullptr && module->Attribution != nullptr)\n'
                   '                ImGui::TextWrapped("%s", module->Attribution);')
    if '#if !defined(__SWITCH__)' not in text:
        text = text.replace(attribution, '#if !defined(__SWITCH__)\n' + attribution + '\n#endif')
    write_if_changed(panel, text)
    immerse_header = engine / 'runtime/three_ds_recomp/include/fast/oot3d/immerse_module_loader.h'
    text = immerse_header.read_text()
    if 'struct TriaevumImmerseModule;' not in text:
        text = text.replace('#include "triaevum/immerse_module.h"',
            '#if defined(__SWITCH__)\nstruct TriaevumImmerseModule;\n#else\n#include "triaevum/immerse_module.h"\n#endif')
    write_if_changed(immerse_header, text)
    stubs = {
        'nri_ngx_vulkan_requirements.cpp': '#include "fast/oot3d/nri_ngx_vulkan_requirements.h"\n'
            'namespace Fast::Oot3d {\nconst NriNgxVulkanRequirements& GetNriNgxVulkanRequirements() {\n'
            'static const NriNgxVulkanRequirements requirements{false, {}, {}, "unavailable", "DLSS is unavailable on Switch"};\n'
            'return requirements; }\n}\n',
        'immerse_module_loader.cpp': '#include "fast/oot3d/immerse_module_loader.h"\n'
            'namespace Fast::Oot3d {\nconst TriaevumImmerseModule* ImmerseModule() { return nullptr; }\n'
            'const std::string& ImmerseModuleUnavailableReason() {\n'
            'static const std::string reason="MXAO is unavailable on Switch"; return reason; }\n}\n',
        'mxao_settings_panel.cpp': '#include "fast/oot3d/graphics_settings_window.h"\n'
            'namespace Fast::Oot3d {\n'
            'bool GraphicsSettingsPanel::DrawMxaoSettings(EffectsSettings&) { return false; }\n'
            'void GraphicsSettingsPanel::DrawMxaoCredits() {}\n}\n',
    }
    for name, stub in stubs.items():
        path = engine / 'runtime/three_ds_recomp/src/fast/oot3d' / name
        text = path.read_text()
        if not text.startswith('#if defined(__SWITCH__)'):
            path.write_text('#if defined(__SWITCH__)\n' + stub + '#else\n' + text + '\n#endif\n')
    main = engine / 'tools/oot3d/native_game_runtime/oot3d_native_game.cpp'
    text = main.read_text()
    start = text.index('        std::array<char*, 21> homebrewArguments{')
    end = text.index('        if (argc <= 1)', start)
    block = text[start:end]
    block = block.replace('const_cast<char*>("topscreen")', 'const_cast<char*>("reframed")')
    block = block.replace('"--topscreen-config"', '"--config"').replace(
        '"sdmc:/switch/oot3dre/config/topscreen_ui.json"', '"sdmc:/switch/oot3dre/config/native-game.json"')
    block = block.replace('"--topscreen-texture-overrides"', '"--renderer-cache-directory"').replace(
        '"sdmc:/switch/oot3dre/config/atlas_overrides.o3tu"', '"sdmc:/switch/oot3dre/cache"')
    text = text[:start] + block + text[end:]
    if 'Switch main entered' not in text:
        text = text.replace('    try {\n#if defined(RETUNED_DESKTOP_SETUP)', '    try {\n#if defined(__SWITCH__)\n        std::puts("Switch main entered");\n        WriteSwitchBootStatus("entered");\n#endif\n#if defined(RETUNED_DESKTOP_SETUP)')
    if 'Switch arguments count=' not in text:
        text = text.replace('        NativeGameArguments preparedArguments;',
            '        NativeGameArguments preparedArguments;\n#if defined(__SWITCH__)\n'
            '        std::printf("Switch arguments count=%d\\n",argc);\n'
            '        for(int i=0;i<argc;++i)std::printf("argv[%d]=%s\\n",i,argv[i]);\n#endif')
        text = text.replace('        if (!ParseOot3dNativeGameArgs(argc, argv, launch)) {',
            '#if defined(__SWITCH__)\n        std::printf("Prepared arguments count=%d\\n",argc);\n'
            '        for(int i=0;i<argc;++i)std::printf("prepared[%d]=%s\\n",i,argv[i]);\n#endif\n'
            '        if (!ParseOot3dNativeGameArgs(argc, argv, launch)) {')
    if 'Switch presentation stays on its OpenGL context thread.' not in text:
        text = text.replace('        SDL_SetHint(SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS, "1");',
            '        SDL_SetHint(SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS, "1");\n'
            '        // Switch presentation stays on its OpenGL context thread.\n'
            '        launch.ParallelPresentation = false;')
    text = text.replace("whole_aot_functions=12419", "whole_aot_functions=unmeasured").replace("host_boundaries=3", "host_boundaries=unmeasured").replace("residual_a32=0", "residual_a32=unmeasured")
    write_if_changed(main, text)
    window = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window.cpp'
    text = window.read_text()
    stack_session = ('  Oot3dA32Window::NativeA32WindowSession session(launch);\n'
                     '  session.Run();')
    if 'make_unique<Oot3dA32Window::NativeA32WindowSession>' not in text:
        text = text.replace(stack_session,
            '#if defined(__SWITCH__)\n'
            '  // Keep the large renderer/session state off the homebrew main stack.\n'
            '  auto session = std::make_unique<Oot3dA32Window::NativeA32WindowSession>(launch);\n'
            '  session->Run();\n#else\n' + stack_session + '\n#endif')
    if 'Switch constructing runtime session' not in text:
        text = text.replace('  auto session = std::make_unique<Oot3dA32Window::NativeA32WindowSession>(launch);',
            '  std::printf("Switch constructing runtime session: %zu bytes\\n",sizeof(Oot3dA32Window::NativeA32WindowSession));\n'
            '  auto session = std::make_unique<Oot3dA32Window::NativeA32WindowSession>(launch);\n'
            '  std::puts("Switch runtime session constructed");')
    setup = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_setup.cpp'
    setup_text = setup.read_text()
    if 'Switch runtime Setup entered' not in setup_text:
        setup_text = setup_text.replace('void NativeA32WindowSession::Setup() {',
            'void NativeA32WindowSession::Setup() {\n#if defined(__SWITCH__)\nstd::puts("Switch runtime Setup entered");\n#endif')
    if 'Switch grass defaults installed' not in setup_text:
        setup_text = setup_text.replace('  Fast::Oot3d::InstallTitleGrassRuleDefaults(Oot3dNativeGame::Oot3dTitleGrassRuleDefaults());',
            '  Fast::Oot3d::InstallTitleGrassRuleDefaults(Oot3dNativeGame::Oot3dTitleGrassRuleDefaults());\n#if defined(__SWITCH__)\nstd::puts("Switch grass defaults installed");\n#endif')
        setup_text = setup_text.replace('  activeTopScreenConfig =',
            '#if defined(__SWITCH__)\nstd::puts("Switch control runtimes constructed");\n#endif\n  activeTopScreenConfig =',1)
        setup_text = setup_text.replace('  manifest = Oot3dNativeGame::LoadNativeA32ProcessImageManifest(',
            '#if defined(__SWITCH__)\nstd::puts("Switch loading manifest");\n#endif\n  manifest = Oot3dNativeGame::LoadNativeA32ProcessImageManifest(',1)
    write_if_changed(setup, setup_text)
    text = text.replace("whole_aot_functions=12419", "whole_aot_functions=unmeasured").replace("host_boundaries=3", "host_boundaries=unmeasured").replace("residual_a32=0", "residual_a32=unmeasured")
    write_if_changed(window, text)
    bootstrap = engine / 'tools/oot3d/native_game_runtime/oot3d_native_game_bootstrap.cpp'
    text = bootstrap.read_text()
    if 'Switch argument parser rejected' not in text:
        text = text.replace('return false;', '#if defined(__SWITCH__)\nstd::fprintf(stderr,"Switch argument parser rejected at line %d\\n",__LINE__);\n#endif\nreturn false;')
        text = '#include <cstdio>\n' + text
    if 'RetunedSwitchAbsolutePath' not in text:
        text = text.replace('std::filesystem::absolute(', 'RetunedSwitchAbsolutePath(')
        helper = ('namespace {\nstd::filesystem::path RetunedSwitchAbsolutePath(const std::filesystem::path& path) {\n'
            '#if defined(__SWITCH__)\nif(path.generic_string().find(":/")!=std::string::npos)return path.lexically_normal();\n#endif\n'
            'return std::filesystem::absolute(path);\n}\n')
        text = text.replace('namespace {\n', helper, 1)
    write_if_changed(bootstrap, text)
    context = engine / 'tools/oot3d/native_demo_host/oot3d_demo_host_context.cpp'
    text = context.read_text()
    if 'PollSwitchLaunchMarkerForDemo' not in text:
        text = text.replace('void ArmLaunchMarker(const std::string& configurationPath) {',
            'std::chrono::steady_clock::time_point SwitchLaunchMarkerDeadline{};\n'
            'void ArmLaunchMarker(const std::string& configurationPath) {')
        text = text.replace('    std::thread([marker] {',
            '#if defined(__SWITCH__)\n'
            '    SwitchLaunchMarkerDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(60);\n'
            '#else\n    std::thread([marker] {',1)
        text = text.replace('    }).detach();', '    }).detach();\n#endif',1)
        marker = 'void InitContextForDemo(const Args& args) {'
        poll = ('void PollSwitchLaunchMarkerForDemo() {\n#if defined(__SWITCH__)\n'
            '    if(SwitchLaunchMarkerDeadline != std::chrono::steady_clock::time_point{} &&\n'
            '       std::chrono::steady_clock::now() >= SwitchLaunchMarkerDeadline) {\n'
            '        ClearLaunchMarkerForDemo();\n'
            '        SwitchLaunchMarkerDeadline = {};\n    }\n#endif\n}\n\n')
        text = text.replace(marker,poll+marker)
    write_if_changed(context,text)
    header = engine / 'tools/oot3d/native_demo_host/oot3d_demo_host_context.h'
    text = header.read_text()
    if 'PollSwitchLaunchMarkerForDemo' not in text:
        text = text.replace('void ClearLaunchMarkerForDemo() noexcept;',
            'void ClearLaunchMarkerForDemo() noexcept;\nvoid PollSwitchLaunchMarkerForDemo();')
    write_if_changed(header,text)
    frame = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_frame.cpp'
    text = frame.read_text()
    if 'PollSwitchLaunchMarkerForDemo' not in text:
        text = text.replace('bool NativeA32WindowSession::RunFrame() {',
            'bool NativeA32WindowSession::RunFrame() {\n#if defined(__SWITCH__)\n'
            '  PollSwitchLaunchMarkerForDemo();\n#endif')
    write_if_changed(frame,text)
    game = engine / 'CMake/oot3d/game.cmake'
    text = game.read_text().replace(
        'NAME "The Legend of Zelda: Ocarina of Time 3D Recompiled"\n        AUTHOR "OoT3D Recompiled contributors"',
        'NAME "Ocarina ReTuned"\n        AUTHOR "OTPR26"')
    text = text.replace('    nx_generate_nacp(oot3d_native_game.nacp\n        NAME "Ocarina ReTuned"\n        AUTHOR "OTPR26"\n        VERSION "0.1.0")', '    add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/oot3d_native_game.nacp"\n        COMMAND "${NX_NACPTOOL_EXE}" --create "Ocarina ReTuned" "OTPR26" "0.1.0"\n            "${CMAKE_CURRENT_BINARY_DIR}/oot3d_native_game.nacp" --titleid=0100F0260A000000\n        VERBATIM)')
    write_if_changed(game, text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    apply(parser.parse_args().engine)
