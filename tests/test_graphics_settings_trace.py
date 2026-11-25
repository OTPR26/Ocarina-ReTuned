import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('trace_patch', ROOT / 'tools/frontend/apply_graphics_settings_trace.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class GraphicsTraceTests(unittest.TestCase):
    def test_patch_is_idempotent_and_marks_lock_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = Path(directory)
            source = engine / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_runtime.cpp'
            source.parent.mkdir(parents=True)
            source.write_text('''GraphicsSettingsValidation GraphicsSettingsRuntime::Apply(GraphicsSettings candidate, bool persist) {
    std::scoped_lock lock(mMutex);
    return ApplyLocked(std::move(candidate), mCapabilities, persist);
}
bool GraphicsSettingsRuntime::PersistCurrentLocked() {
    return true;
}
''')
            frame = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_frame.cpp'
            frame.parent.mkdir(parents=True)
            frame.write_text('presentationPacingPolicy, requestedPresentationPolicy)) {\ncompositionModeChanged] {\n    frameCompositionPolicy')
            patch.apply(engine)
            first = source.read_text()
            first_frame = frame.read_text()
            patch.apply(engine)
            self.assertEqual(first, source.read_text())
            self.assertEqual(first_frame, frame.read_text())
            self.assertLess(first.index('trace("apply")'), first.index('lock(mMutex)'))
            self.assertGreater(first.index('lock-acquired'), first.index('lock(mMutex)'))

    def test_android_trace_and_desktop_silence(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'test.cpp'
            source.write_text('#include "graphics_settings_trace.h"\nint main(){RetunedFrontend::GraphicsSettingsTrace t("apply"); t.Mark("lock-acquired");}\n')
            for android in (False, True):
                binary = Path(directory) / ('android' if android else 'desktop')
                command = [compiler, '-std=c++17', '-I', str(ROOT / 'tools/frontend'), str(source), '-o', str(binary)]
                if android:
                    command.append('-D__ANDROID__')
                subprocess.run(command, check=True, capture_output=True)
                result = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
                if android:
                    self.assertEqual(len(result.stderr.splitlines()), 3)
                    for phase in ('begin', 'lock-acquired', 'end'):
                        self.assertIn('phase=' + phase, result.stderr)
                else:
                    self.assertEqual(result.stderr, '')
