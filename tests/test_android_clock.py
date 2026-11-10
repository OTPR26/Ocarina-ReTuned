"""Verify the Android clock overlay against the pinned native sources."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'android_clock', ROOT / 'tools/native/apply_android_clock.py')
clock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clock)
BASE = '17218b0cfdb944645bb5cde5249f313dca7e53ce'
ENGINE = Path(os.environ.get('RETUNED_RUNTIME_ROOT', ROOT / 'engine'))
NATIVE = Path('tools/oot3d/native_game_runtime')
IMAGE = NATIVE / 'oot3d_native_a32_process_image.cpp'
FRAME = NATIVE / 'oot3d_native_a32_window_frame.cpp'
HEADER = NATIVE / 'oot3d_native_a32_clock.h'


@unittest.skipUnless((ENGINE / '.git').exists(), 'requires the pinned runtime checkout')
class AndroidClockOverlayTests(unittest.TestCase):
    def stage_sources(self, root):
        for name in (IMAGE, FRAME):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(
                ['git', '-C', str(ENGINE), 'show', f'{BASE}:{name.as_posix()}']))

    def test_overlay_preserves_changes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.stage_sources(root)
            for name in (IMAGE, FRAME):
                path = root / name
                path.write_text(path.read_text(encoding='utf-8') + '\n// Other port change.\n', encoding='utf-8')
            clock.apply(root)
            first = {name: (root / name).read_bytes() for name in (IMAGE, FRAME, HEADER)}
            clock.apply(root)
            self.assertEqual(first, {name: (root / name).read_bytes() for name in first})
            for name in (IMAGE, FRAME):
                self.assertTrue((root / name).read_text(encoding='utf-8').endswith('// Other port change.\n'))
            self.assertIn(b'InitializeSharedPageClock', first[IMAGE])
            self.assertIn(b'PublishSharedPageClock', first[FRAME])
            self.assertNotIn(b'cannot update CTR shared-page clock', first[FRAME])
            self.assertNotIn(b'cannot initialize CTR shared-page clock', first[IMAGE])
            self.assertEqual(first[HEADER], (ROOT / 'tools/native/android/oot3d_native_a32_clock.h').read_bytes())

    def test_unexpected_source_leaves_all_files_unmodified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.stage_sources(root)
            path = root / FRAME
            text = path.read_text(encoding='utf-8').replace(
                '  auto &dspHle = *dspHleStorage;\n#if defined(TRIAEVUM_DEVELOPER_TOOLS)',
                '  // Changed upstream context.\n#if defined(TRIAEVUM_DEVELOPER_TOOLS)')
            path.write_text(text, encoding='utf-8')
            before = {name: (root / name).read_bytes() for name in (IMAGE, FRAME)}
            with self.assertRaisesRegex(ValueError, 'frame refresh context changed'):
                clock.apply(root)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})
            self.assertFalse((root / HEADER).exists())

    def test_different_existing_header_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.stage_sources(root)
            (root / HEADER).write_text('// Existing header.\n', encoding='utf-8')
            before = {name: (root / name).read_bytes() for name in (IMAGE, FRAME, HEADER)}
            with self.assertRaisesRegex(ValueError, 'header already exists'):
                clock.apply(root)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})


class AndroidClockNativeTests(unittest.TestCase):
    def test_clock_reference_behaviour(self):
        import shutil
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("C++ compiler is not available")
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "android-clock-test"
            subprocess.run([compiler, "-std=c++20", "-I", str(ROOT / "tools/native/android"),
                            str(ROOT / "tests/android_clock.cpp"), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
