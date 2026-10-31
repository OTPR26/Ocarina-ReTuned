from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools/frontend'), str(ROOT/'tools/reframed')]
from apply_game_save import apply


class GameSaveTests(unittest.TestCase):
    def test_input_delivery_and_dual_only_menu(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires a C++ compiler')
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            output = folder/'input'
            subprocess.run([compiler, '-std=c++20', str(ROOT/'tests/game_save.cpp'), '-o', str(output)], check=True, capture_output=True)
            subprocess.run([str(output)], check=True)
            shutil.copy2(ROOT/'tools/frontend/game_save.h', folder/'retuned_game_save.h')
            (folder/'imgui.h').write_text('''#pragma once
namespace ImGui {
inline int Buttons=0; inline bool Disabled=false;
inline void BeginDisabled(bool value){Disabled=value;}
inline bool Button(const char*){++Buttons;return !Disabled;}
inline void EndDisabled(){} inline void TextWrapped(const char*){} inline void Spacing(){}
}
''')
            (folder/'menu.cpp').write_text('''#include "game_save_menu.h"
#include <cassert>
int main(){using namespace RetunedFrontend;
 GameSave.SetAvailable(true);
 DrawDualGameSave(false,true);DrawDualGameSave(true,false);
 assert(ImGui::Buttons==0&&!GameSave.Pending());
 GameSave.SetAvailable(false);DrawDualGameSave(true,true);
 assert(ImGui::Buttons==1&&!GameSave.Pending());
 GameSave.SetAvailable(true);DrawDualGameSave(true,true);
 assert(ImGui::Buttons==2&&GameSave.Pending());
}
''')
            output=folder/'menu'
            subprocess.run([compiler,'-std=c++20','-I'+str(folder),'-I'+str(ROOT/'tools/frontend'),str(folder/'menu.cpp'),'-o',str(output)],check=True,capture_output=True)
            subprocess.run([str(output)],check=True)

    def test_staging_retains_device_controls_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            frame=root/'tools/oot3d/native_game_runtime/oot3d_native_a32_window_frame.cpp'
            frame.parent.mkdir(parents=True)
            frame.write_text('RouteSettingsButton();\n  if (!inputTimeline.Enabled()) {\nObserveNativeA32PolledButton();\n}\n')
            graphics=root/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
            graphics.parent.mkdir(parents=True)
            graphics.write_text('      case SettingsPage::General: {\nDrawPlatformDisplaySettings();\nAndroidAndDuoControls();\n')
            gui=root/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
            gui.parent.mkdir(parents=True,exist_ok=True)
            gui.write_text('/* existing GUI */\n')
            apply(root)
            first=frame.read_text(),graphics.read_text()
            apply(root)
            self.assertEqual(first,(frame.read_text(),graphics.read_text()))
            self.assertLess(first[0].index('RouteSettingsButton'),first[0].index('GameSave.Take'))
            self.assertLess(first[0].index('GameSave.Take'),first[0].index('ObserveNativeA32PolledButton'))
            self.assertIn('AndroidAndDuoControls();',first[1])
            self.assertEqual(first[1].count('DrawDualGameSave('),1)
