"""Select a validated bundled QBF face before native character lookup."""
from pathlib import Path


def apply(root):
    base=Path(root)/'tools/oot3d/native_game_runtime'
    patches=[
      ('oot3d_native_hd_font_runtime.h',
       'inline constexpr std::uint32_t kNativeQbfA4Blit = 0x002d2504;',
       'inline constexpr std::uint32_t kNativeQbfA4Blit = 0x002d2504;\ninline constexpr std::uint32_t kNativeQbfLookup = 0x002d2674;'),
      ('oot3d_native_hd_font_runtime.h',
       'bool Load(const std::filesystem::path& path, std::string* error);',
       'bool Load(const std::filesystem::path& path, std::string* error, const std::string& style = "bold");\n    void ObserveLookup(const oot3d::recomp::a32::GuestState& state, NativeA32Memory& memory);\n    bool HasStyleChoices() const { return mHasStyleChoices; }\n    std::uint64_t StyleSelections = 0;'),
      ('oot3d_native_hd_font_runtime.h',
       '        NativeFontCoverage Coverage;',
       '        NativeFontCoverage Coverage;\n        std::string Style;'),
      ('oot3d_native_hd_font_runtime.h',
       '    std::vector<Font> mFonts;',
       '    std::vector<Font> mFonts;\n    std::vector<std::vector<std::uint8_t>> mNativeSources;\n    std::size_t mSelectedFont = 0;\n    bool mHasStyleChoices = false;'),
      ('oot3d_native_hd_font_runtime.cpp',
       'bool NativeHdFontRuntime::Load(const std::filesystem::path& path, std::string* error) {',
       Path(__file__).with_name('font_choices.cpp.inc').read_text()+'\nbool NativeHdFontRuntime::Load(const std::filesystem::path& path, std::string* error, const std::string& style) {'),
      ('oot3d_native_hd_font_runtime.cpp',
       '            Font font;\n            font.Native',
       '            Font font;\n            font.Style = entry.value("style", std::string{});\n            font.Native'),
      ('oot3d_native_hd_font_runtime.cpp',
       '        mFonts = std::move(fonts);',
       '''        std::vector<std::vector<std::uint8_t>> sources;
        bool regular=false, bold=false;
        std::size_t selected=0;
        for (std::size_t i=0; i<fonts.size(); ++i) {
            regular |= fonts[i].Style == "regular";
            bold |= fonts[i].Style == "bold";
            if (fonts[i].Style == (style == "regular" ? "regular" : "bold")) selected=i;
            sources.push_back(fonts[i].Native);
        }
        if (manifest.contains("native_sources")) {
            if (manifest.at("native_sources").size() > 8) throw std::runtime_error("too many native font sources");
            for (const auto& name : manifest.at("native_sources"))
                sources.push_back(ReadZip(zip,name.get<std::string>()));
        }
        if (regular && bold) {
            for (const auto& source : sources)
                for (const auto& font : fonts)
                    if (!CompatibleFontAllocation(source,font.Native))
                        throw std::runtime_error("font choice cannot fit the native allocation");
        }
        mNativeSources=std::move(sources);
        mSelectedFont=selected;
        mHasStyleChoices=regular && bold;
        mFonts = std::move(fonts);'''),
      ('oot3d_native_a32_window_setup.cpp',
       '      hdFontsLoaded = hdFonts.Load(fontPath, &error);',
       '''      // Font resources load before the UI context exists; read the same config
      // directly rather than silently falling back on every startup.
      Ship::Config fontConfig(launch.Host.ConfigurationPath);
      const auto fontStyle=fontConfig.GetString("Interface.DialogueFontWeight", "bold");
      RetunedFrontend::ActiveDialogueFontWeight=fontStyle == "regular" ? "regular" : "bold";
      hdFontsLoaded = hdFonts.Load(selectedFontPath, &error, RetunedFrontend::ActiveDialogueFontWeight);
      RetunedFrontend::DialogueFontChoicesAvailable=hdFontsLoaded && hdFonts.HasStyleChoices();'''),
      ('oot3d_native_a32_window_setup.cpp',
       '  if (hdFontsLoaded) blockEntryHooks.push_back(Oot3dNativeGame::kNativeQbfA4Blit);',
       '  if (hdFontsLoaded) {\n    blockEntryHooks.push_back(Oot3dNativeGame::kNativeQbfA4Blit);\n    blockEntryHooks.push_back(Oot3dNativeGame::kNativeQbfLookup);\n  }'),
      ('oot3d_native_a32_projection_policy.cpp',
       '  if (pc == Oot3dNativeGame::kNativeQbfA4Blit && runtime.HdFonts && runtime.TraceMemory)',
       '  if (pc == Oot3dNativeGame::kNativeQbfLookup && runtime.HdFonts && runtime.TraceMemory)\n    runtime.HdFonts->ObserveLookup(state, *runtime.TraceMemory);\n  if (pc == Oot3dNativeGame::kNativeQbfA4Blit && runtime.HdFonts && runtime.TraceMemory)'),
    ]
    patches.append(('oot3d_native_a32_window_summary.cpp',
        '{"hd_font_native_blits", hdFonts.Blits},',
        '{"hd_font_native_blits", hdFonts.Blits},\n                   {"hd_font_style_selections", hdFonts.StyleSelections},\n                   {"hd_font_style_choices", hdFonts.HasStyleChoices()},'))
    patches.append(('oot3d_native_a32_window_setup.cpp',
        '    if (std::filesystem::is_regular_file(fontPath)) {',
        '''    // Apple mobile keeps packaged resources separate from writable settings.
    // Prefer an installation-local pack; fall back to the app resource root.
    const auto bundledFontPath = std::filesystem::path(launch.Host.ResourceRoot) / "font_coverage.zip";
    const auto selectedFontPath = std::filesystem::is_regular_file(fontPath)
        ? fontPath : bundledFontPath;
    if (std::filesystem::is_regular_file(selectedFontPath)) {'''))
    test_marker='        std::filesystem::remove(path);\n        std::cout << "HD font runtime'
    test_code=Path(__file__).with_name('font_choices_tests.cpp.inc').read_text()
    patches.append(('oot3d_native_hd_font_runtime_tests.cpp',test_marker,test_code+test_marker))
    for name,before,after in patches:
        p=base/name;s=p.read_text()
        if after in s:continue
        if s.count(before)!=1:raise ValueError('Dialogue font choice context changed: '+name)
        p.write_text(s.replace(before,after))
