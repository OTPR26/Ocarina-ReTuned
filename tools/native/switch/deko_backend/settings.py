"""Register shared Settings for deko3d and expose supported Switch controls."""
from pathlib import Path


def replace(path, before, after):
    text = path.read_text()
    if after in text:
        return
    if text.count(before) != 1:
        raise ValueError('Switch settings context changed: ' + path.name)
    path.write_text(text.replace(before, after))


def apply(engine):
    runtime = Path(engine) / 'runtime/three_ds_recomp'
    gui = runtime / 'src/fast/Fast3dGui.cpp'
    replace(gui, 'namespace {\n#ifdef ENABLE_OOT3D_VULKAN\nclass Oot3dGraphicsSettingsPersistence',
        'namespace {\n#if defined(ENABLE_OOT3D_VULKAN) || defined(RETUNED_SWITCH_DEKO)\nclass Oot3dGraphicsSettingsPersistence')
    replace(gui, '\nstruct Oot3dMousePosition {',
        '\n#endif\n#ifdef ENABLE_OOT3D_VULKAN\nstruct Oot3dMousePosition {')
    replace(gui, '    Gui::Init();', '''#ifdef RETUNED_SWITCH_DEKO
    // The shared Settings window is also needed by the native Switch renderer.
    Oot3d::InstallGraphicsSettingsPersistencePort(
        std::make_shared<Oot3dGraphicsSettingsPersistence>());
    AddGuiWindow(std::make_shared<Oot3dGraphicsSettingsWindow>());
    AddGuiWindow(std::make_shared<Oot3dHostNoticeWindow>());
#endif
    Gui::Init();''')
    replace(gui, 'void Fast3dGui::ToggleOot3dGraphicsWindow() {\n#ifdef ENABLE_OOT3D_VULKAN',
        '''void Fast3dGui::ToggleOot3dGraphicsWindow() {
#ifdef RETUNED_SWITCH_DEKO
    if (auto settingsWindow = GetGuiWindow("OOT3D Graphics")) settingsWindow->ToggleVisibility();
#elif defined(ENABLE_OOT3D_VULKAN)''')
    replace(gui, '#else\n            if(!RetunedFrontend::TouchPlatform())ImGui::TextDisabled("Control + comma: settings");',
        '#elif defined(RETUNED_SWITCH_DEKO)\n            ImGui::TextDisabled("Minus: settings. B: back.");\n#else\n            if(!RetunedFrontend::TouchPlatform())ImGui::TextDisabled("Control + comma: settings");')
    panel = runtime / 'src/fast/oot3d/graphics_settings_window.cpp'
    replace(panel, '      case SettingsPage::Graphics:\n        if(!mobile)DrawPresetSelector();',
        '''      case SettingsPage::Graphics:
#ifdef RETUNED_SWITCH_DEKO
        DrawSettingsSections({&GraphicsSettingsPanel::DrawMotionSettings});
        drawTabs("Camera");
        ImGui::TextWrapped("Switch output: 1280 x 720. Desktop effects and display modes are unavailable.");
        ImGui::SeparatorText("Custom textures");DrawTextureSettings();
#else
        if(!mobile)DrawPresetSelector();''')
    replace(panel, '            DrawLightingTab(lighting);\n        }\n        break;',
        '            DrawLightingTab(lighting);\n        }\n#endif\n        break;')
    categories = runtime / 'include/fast/oot3d/retuned_settings_pages.h'
    replace(categories, ' if(page==SettingsPage::Touch)return touch;',
        '#ifdef RETUNED_SWITCH_DEKO\n if(page==SettingsPage::Touch||page==SettingsPage::Advanced)return false;\n#endif\n if(page==SettingsPage::Touch)return touch;')

    textures = runtime / 'src/fast/oot3d/azahar_texture_pack_panel.cpp'
    replace(textures, '    if(RetunedFrontend::MobileSettingsPlatform()) {',
        '#ifdef RETUNED_SWITCH_DEKO\n    if(true) { // SD-card pack controls; no desktop path editor or dump tools.\n#else\n    if(RetunedFrontend::MobileSettingsPlatform()) {\n#endif')
    replace(textures, '        if(RetunedFrontend::TelevisionPlatform())\n',
        '#ifdef RETUNED_SWITCH_DEKO\n        ImGui::TextWrapped("Uses the texture folder configured during desktop preparation. Copy your pack to that folder on the SD card, then reload textures.");\n#else\n        if(RetunedFrontend::TelevisionPlatform())\n')
    replace(textures, '        auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();',
        '#endif\n        auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();')
    replace(gui, '        RetunedFrontend::SettingsNav.Begin(RetunedFrontend::TelevisionPlatform());',
        '#ifdef RETUNED_SWITCH_DEKO\n        RetunedFrontend::SettingsNav.Begin(true);\n#else\n        RetunedFrontend::SettingsNav.Begin(RetunedFrontend::TelevisionPlatform());\n#endif')
    display = runtime / 'src/fast/oot3d/graphics_settings_display_panel.cpp'
    replace(display, '''    const char* const frameRates[] = {
        "Original 30 FPS", "Interpolated 2x (60 FPS)",
        "Interpolated 3x (90 FPS)", "Uncapped"};
    changed |= EnumCombo("Frame rate", settings.FrameRate, frameRates);''', '''#ifdef RETUNED_SWITCH_DEKO
    int switchRate = settings.FrameRate == FrameRateMode::Interpolated2x ? 1 : 0;
    if (ImGui::Combo("Frame rate", &switchRate,
            "30 FPS (default)\\0" "60 FPS (experimental)\\0")) {
        settings.FrameRate = switchRate ? FrameRateMode::Interpolated2x : FrameRateMode::Original30;
        changed = true;
    }
    if (switchRate) ImGui::TextWrapped("Interpolated 60 FPS. Performance on physical Switch hardware is unverified; use 30 FPS if frame pacing suffers.");
#else
    const char* const frameRates[] = {
        "Original 30 FPS", "Interpolated 2x (60 FPS)",
        "Interpolated 3x (90 FPS)", "Uncapped"};
    changed |= EnumCombo("Frame rate", settings.FrameRate, frameRates);
#endif''')
    settings = runtime / 'src/fast/oot3d/graphics_settings_runtime.cpp'
    replace(settings, '    if (selectedInitial) {\n        mService = GraphicsSettingsService(std::move(initial));', '''#ifdef RETUNED_SWITCH_DEKO
    // Preserve an explicit 60 FPS choice; retire old 90/uncapped settings.
    if (initial.FrameRate != FrameRateMode::Original30 &&
        initial.FrameRate != FrameRateMode::Interpolated2x) {
        initial.FrameRate = FrameRateMode::Original30;
        selectedInitial = true;
        rewriteLoadedSettings = true;
    }
#endif
    if (selectedInitial) {
        mService = GraphicsSettingsService(std::move(initial));''')

    memory = runtime / 'include/fast/oot3d/texture_memory_platform.h'
    replace(memory, '#elif defined(__APPLE__)\n    return true;',
        '#elif defined(__APPLE__) || defined(RETUNED_SWITCH_DEKO)\n    return true;')
    replace(memory, '#if defined(__APPLE__) && TARGET_OS_TV\n    return true;',
        '#if defined(RETUNED_SWITCH_DEKO) || (defined(__APPLE__) && TARGET_OS_TV)\n    return true;')
