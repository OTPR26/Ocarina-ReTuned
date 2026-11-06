from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MinimapToggleTests(unittest.TestCase):
    def test_trigger_edges_and_native_visibility(self):
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('Requires a C compiler')
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / 'minimap'
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                str(ROOT / 'tests/minimap_toggle.c'), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_canonical_source_staging(self):
        source = os.environ.get('RETUNED_REFRAMED_SOURCE')
        if not source:
            self.skipTest('Requires the local canonical ReFramed source')
        spec = importlib.util.spec_from_file_location('minimap_stage',
            ROOT / 'tools/reframed/apply_minimap_toggle.py')
        stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'src').mkdir()
            (root / 'include').mkdir()
            for name in ('BUILD.txt', 'src/input_remap.c'):
                shutil.copy2(Path(source) / name, root / name)
            original = (root / 'src/input_remap.c').read_text()
            stage.apply(root)
            once = (root / 'src/input_remap.c').read_bytes()
            stage.apply(root)
            self.assertEqual(once, (root / 'src/input_remap.c').read_bytes())
            text = once.decode()
            self.assertNotIn('sMinimapAssumedVisible', text)
            self.assertNotIn('sMinimapHideFrames', text)
            self.assertNotIn('MINIMAP_HIDE_HOLD_FRAMES', text)
            self.assertEqual(text.count('const u32 irrstButtons = irrstKeysHeld();'), 1)
            self.assertEqual(text.count('ManualJump_Apply('), original.count('ManualJump_Apply('))
            self.assertIn('RetunedMinimap_Update(irrstPressed,', text)
            self.assertIn('!InputRemap_IsItemsMenuOpen()', text)
            self.assertEqual((root / 'include/minimap_toggle.h').read_bytes(),
                (ROOT / 'tools/reframed/minimap_toggle.h').read_bytes())
