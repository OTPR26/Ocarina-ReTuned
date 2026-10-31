from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlatformDisplaySettingsTests(unittest.TestCase):
    def test_android_duo_and_desktop_controls_and_persistence(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires a C++20 compiler')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'imgui.h').write_text('''#pragma once
#include <algorithm>
#include <string>
#include <vector>
namespace ImGui {
inline std::vector<std::string> Labels;
inline int NextMode=-1;
inline bool ChangePanel=false;
inline bool Saw(const char* label){return std::find(Labels.begin(),Labels.end(),label)!=Labels.end();}
inline void SeparatorText(const char*){}
inline void TextWrapped(const char*,...){}
inline bool Combo(const char* label,int* value,const char*){
 Labels.emplace_back(label);if(NextMode<0)return false;*value=NextMode;NextMode=-1;return true;
}
inline bool Checkbox(const char* label,bool* value){
 Labels.emplace_back(label);if(!ChangePanel)return false;*value=!*value;ChangePanel=false;return true;
}
}
''')
            shutil.copy2(ROOT / 'tools/native/android/dual_screen/display_state.h', root / 'android_display_state.h')
            (root / 'retuned_screen_probe.h').write_text('''#pragma once
#include "duo_game_display.h"
namespace RetunedFrontend {
inline bool DuoProbeRequested(){
#ifdef TEST_DESKTOP
return false;
#else
return true;
#endif
}
}
''')
            for name, flags in (('android', ['-D__ANDROID__']), ('duo', ['-D__APPLE__']), ('desktop', ['-DTEST_DESKTOP'])):
                with self.subTest(platform=name):
                    output = root / name
                    subprocess.run([compiler, '-std=c++20', *flags, '-I' + str(root),
                        '-I' + str(ROOT / 'tools/frontend'),
                        str(ROOT / 'tests/platform_display_settings.cpp'), '-o', str(output)],
                        check=True, capture_output=True)
                    subprocess.run([str(output)], check=True, capture_output=True)

    def test_switch_categories_keep_the_platform_filter(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires a C++20 compiler')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'switch-categories'
            subprocess.run([compiler, '-std=c++20', '-DRETUNED_SWITCH_DEKO',
                str(ROOT / 'tests/settings_categories.cpp'), '-o', str(output)],
                check=True, capture_output=True)
            subprocess.run([str(output)], check=True, capture_output=True)
