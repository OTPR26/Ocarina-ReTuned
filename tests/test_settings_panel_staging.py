from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/frontend'))
from panel_staging import refresh_mods_page


class SettingsPanelStagingTests(unittest.TestCase):
    def test_existing_build_gets_mods_without_losing_device_controls(self):
        for old in ('', '      case SettingsPage::Mods:\n        break;\n'):
            with self.subTest(old=old), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
                path.parent.mkdir(parents=True)
                before = 'void Draw() {\n// device-specific screen-mode controls\n'
                after = '      case SettingsPage::About:\n// existing remaining pages\n}\n'
                path.write_text(before + old + after)
                refresh_mods_page(root)
                contents = path.read_text()
                self.assertTrue(contents.startswith(before))
                self.assertTrue(contents.endswith(after))
                self.assertEqual(contents.count('case SettingsPage::Mods:'), 1)
                self.assertIn('RequestPlayerModels', contents)
                self.assertIn('DrawAndroidMods', contents)
                self.assertIn('desktop game preparation', contents)
                stamp = path.stat().st_mtime_ns
                refresh_mods_page(root)
                self.assertEqual(path.read_text(), contents)
                self.assertEqual(path.stat().st_mtime_ns, stamp)

    def test_changed_anchor_fails_without_editing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
            path.parent.mkdir(parents=True)
            path.write_text('unexpected source')
            with self.assertRaises(ValueError):
                refresh_mods_page(root)
            self.assertEqual(path.read_text(), 'unexpected source')
