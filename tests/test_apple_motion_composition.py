import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AppleMotionCompositionTests(unittest.TestCase):
    def test_stick_turning_preserves_physical_pitch(self):
        source=ROOT/'work/reference/triaevum/tools/three_ds/input'
        compiler=shutil.which('clang++')
        if not compiler or not (source/'three_ds_motion_composition.cpp').exists():
            self.skipTest('Requires native compiler and pinned engine')
        spec=importlib.util.spec_from_file_location('motion_patch',ROOT/'tools/native/apple/patch_motion_composition.py')
        patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
        with tempfile.TemporaryDirectory() as directory:
            engine=Path(directory);target=engine/'tools/three_ds/input'
            target.mkdir(parents=True)
            for name in ('three_ds_motion_composition.cpp','three_ds_motion_composition.h'):
                shutil.copy2(source/name,target/name)
            patch.apply(engine);before=(target/'three_ds_motion_composition.cpp').read_bytes()
            patch.apply(engine);self.assertEqual(before,(target/'three_ds_motion_composition.cpp').read_bytes())
            output=engine/'motion-test'
            subprocess.run([compiler,'-std=c++20','-I'+str(target),str(ROOT/'tests/apple_motion_composition.cpp'),str(target/'three_ds_motion_composition.cpp'),'-o',str(output)],check=True,capture_output=True)
            subprocess.run([str(output)],check=True,capture_output=True)
