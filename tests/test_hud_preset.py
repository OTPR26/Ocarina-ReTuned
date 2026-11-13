from pathlib import Path
import importlib.util
import os
import sys
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HudPresetTests(unittest.TestCase):
    def test_touch_action_and_ammo_placement(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires a C++ compiler')
        with tempfile.TemporaryDirectory() as temp:
            exe = Path(temp) / 'touch'
            subprocess.run([compiler, '-std=c++20', str(ROOT / 'tests/touch_hud.cpp'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

    def test_native_mapping_and_idempotent_staging(self):
        source = os.environ.get('RETUNED_REFRAMED_SOURCE')
        if not source:
            self.skipTest('Requires the local canonical ReFramed source')
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('Requires a C compiler')
        sys.path.insert(0,str(ROOT / 'tools/reframed'))
        spec = importlib.util.spec_from_file_location('hud_stage', ROOT / 'tools/reframed/apply_hud_preset.py')
        stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'src').mkdir(); (root / 'include').mkdir()
            for name in ('BUILD.txt', 'src/controls.c', 'src/input_remap.c', 'src/native_hud.c', 'include/controls.h', 'include/hid.h'):
                shutil.copy2(Path(source) / name, root / name)
            stage.apply(root)
            once = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            stage.apply(root)
            self.assertTrue(all(p.read_bytes() == data for p, data in once.items()))
            exe = root / 'mapping'
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I' + str(root / 'include'),
                str(ROOT / 'tests/hud_preset.c'), str(root / 'src/hud_preset.c'), str(root / 'src/controls.c'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
            # Exercise the actual staged geometry helper, preserving icon sizes.
            hud = (root / 'src/native_hud.c').read_text()
            start = hud.index('static void NativeHud_PositionPreset(void) {')
            end = hud.index('\nstatic u32 sNativeHudGroupScale', start)
            geometry = root / 'geometry.c'
            geometry.write_text('#include "hud_preset.h"\n#include <assert.h>\n'
                'static float dx[33],dy[33];\nstatic int sNativeHudDualMenuLayout,sNativeHudOcarinaLayout;\n'
                'static void NativeHud_TranslateQuad(unsigned q,float x,float y){dx[q]+=x;dy[q]+=y;}\n'
                + hud[start:end] + '\nint main(void){\n'
                'NativeHud_PositionPreset();for(unsigned q=0;q<33;++q)assert(dx[q]==0&&dy[q]==0);\n'
                'HudPreset_Set(1);NativeHud_PositionPreset();\n'
                'assert(dx[8]==-34&&dy[8]==0);assert(dx[9]==17&&dy[9]==20);\n'
                'assert(dx[10]==17&&dy[10]==-20);assert(dx[12]==dx[10]&&dy[12]==dy[10]);\n'
                'assert(dx[5]==-17&&dy[5]==-17);assert(dx[7]==17&&dy[7]==17);assert(dx[29]==17&&dy[29]==17);\n'
                'for(unsigned q=0;q<33;++q)if(q!=5&&q!=7&&q!=29&&q!=8&&q!=9&&q!=10&&q!=12)assert(dx[q]==0&&dy[q]==0);\n'
                'for(unsigned q=0;q<33;++q)dx[q]=dy[q]=0;\n'
                'sNativeHudDualMenuLayout=1;NativeHud_PositionPreset();assert(dx[5]==0&&dy[5]==0&&dx[7]==0&&dy[7]==0);\n'
                'sNativeHudDualMenuLayout=0;sNativeHudOcarinaLayout=1;NativeHud_PositionPreset();assert(dx[5]==0&&dy[5]==0&&dx[7]==0&&dy[7]==0);\n'
                'HudPreset_Set(0);NativeHud_PositionPreset();assert(dx[8]==-68);return 0;}\n')
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I' + str(root / 'include'),
                str(geometry), str(root / 'src/hud_preset.c'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
