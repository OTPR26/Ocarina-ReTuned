from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MobileMotionTests(unittest.TestCase):
    def test_device_sensors_orientation_and_lifecycle(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        source = ROOT / 'work/reference/triaevum/tools/three_ds/input'
        if not compiler or not (source / 'three_ds_input.cpp').exists():
            self.skipTest('Requires a C++20 compiler and the pinned runtime checkout')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'motion'
            subprocess.run([compiler, '-std=c++20', '-I'+str(ROOT/'tests/mobile_motion_stub'),
                '-I'+str(source), str(ROOT/'tests/mobile_device_motion.cpp'),
                str(source/'three_ds_input.cpp'), str(source/'three_ds_motion_composition.cpp'),
                '-o', str(output)],check=True,capture_output=True)
            subprocess.run([str(output)],check=True,capture_output=True)

    def test_input_overlay_is_idempotent(self):
        sys.path[:0] = [str(ROOT/'tools/frontend'),str(ROOT/'tools/reframed')]
        from apply_mobile_motion import apply
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'runtime/three_ds_recomp/include/fast/oot3d').mkdir(parents=True)
            path=root/'tools/oot3d/native_game_runtime/oot3d_native_a32_window_input.cpp'
            path.parent.mkdir(parents=True)
            path.write_text('#include "oot3d_native_a32_window_shared.h"\n  controls.ObserveMotion(host.ControllerMotion);\n')
            apply(root);original=path.read_text();apply(root)
            self.assertEqual(path.read_text(),original)
            self.assertEqual(original.count('SampleMobileDeviceMotion('),1)
