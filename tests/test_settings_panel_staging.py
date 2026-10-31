from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/frontend'))
from panel_staging import refresh_mods_page, refresh_panel_draw, stage_platform_display_settings


class SettingsPanelStagingTests(unittest.TestCase):
    def test_full_shared_refresh_keeps_display_controls_on_repeated_application(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
            path.parent.mkdir(parents=True)
            tail = '\nvoid GraphicsSettingsPanel::DrawGrassSettings() { /* retained renderer */ }\n'
            path.write_text('void GraphicsSettingsPanel::Draw() { old_page(); }\n' + tail)
            refresh_panel_draw(root)
            first = path.read_text()
            self.assertIn('DrawPlatformDisplaySettings(config,RetunedFrontend::Toggle)', first)
            self.assertEqual(first.count('DrawPlatformDisplaySettings('), 1)
            self.assertTrue(first.endswith(tail))
            header = root / 'runtime/three_ds_recomp/include/fast/oot3d/retuned_platform_display_settings.h'
            self.assertIn('Screen mode', header.read_text())
            stamp = path.stat().st_mtime_ns, header.stat().st_mtime_ns
            refresh_panel_draw(root)
            self.assertEqual(path.read_text(), first)
            self.assertEqual((path.stat().st_mtime_ns, header.stat().st_mtime_ns), stamp)

    def test_legacy_platform_overlays_migrate_without_duplicate_controls(self):
        conditions = ('RetunedFrontend::AndroidDualProbeRequested()',
                      'RetunedFrontend::DuoProbeRequested() && RetunedFrontend::DuoDisplay.Available()')
        for condition in conditions:
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
                path.parent.mkdir(parents=True)
                path.write_text('before\n        if(' + condition + ') {\n'
                    '            ImGui::SeparatorText("Display");\n'
                    '            if (selected) { legacy_controls(); }\n        }\n'
                    '        ImGui::SeparatorText("Menu");\nafter\n')
                stage_platform_display_settings(root)
                contents = path.read_text()
                self.assertNotIn('legacy_controls', contents)
                self.assertIn('DrawPlatformDisplaySettings(', contents)
                self.assertTrue(contents.endswith('after\n'))

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
