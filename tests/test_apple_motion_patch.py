"""Apple controllers can expose total acceleration without gravity separation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('apple_motion_patch', ROOT/'tools/native/apple/patch_sdl_motion.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

class AppleMotionPatchTests(unittest.TestCase):
    def fixture(self, root):
        target = root/'src/joystick/iphoneos/SDL_mfijoystick.m'
        target.parent.mkdir(parents=True)
        target.write_text('''if (motion && motion.hasRotationRate) {
                    SDL_PrivateJoystickAddSensor(joystick, SDL_SENSOR_GYRO, 0.0f);
                }
                if (motion && motion.hasGravityAndUserAcceleration) {
                    SDL_PrivateJoystickAddSensor(joystick, SDL_SENSOR_ACCEL, 0.0f);
                }
                if (motion && motion.sensorsActive) {
                    if (motion.hasRotationRate) {
                        GCRotationRate rate = motion.rotationRate;
                        data[0] = rate.x;
                        data[1] = rate.z;
                        data[2] = -rate.y;
                    }
                    if (motion.hasGravityAndUserAcceleration) {
                        GCAcceleration accel = motion.acceleration;
                        data[0] = -accel.x * SDL_STANDARD_GRAVITY;
                        data[1] = -accel.y * SDL_STANDARD_GRAVITY;
                        data[2] = -accel.z * SDL_STANDARD_GRAVITY;
                    }
                }
''')
        return target

    def test_total_acceleration_without_separation_and_gyro_guards_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = self.fixture(root)
            patch.apply(root)
            result = target.read_text()
            self.assertNotIn('hasGravityAndUserAcceleration', result)
            self.assertIn('if (motion) {\n                    SDL_PrivateJoystickAddSensor(joystick, SDL_SENSOR_ACCEL', result)
            self.assertIn('if (motion && motion.sensorsActive)', result)
            self.assertIn('if (motion && motion.hasRotationRate)', result)
            self.assertIn('GCAcceleration accel = motion.acceleration;', result)
            patch.apply(root)
            self.assertEqual(result, target.read_text())

    def test_changed_sdl_context_fails_without_partial_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = self.fixture(root)
            target.write_text(target.read_text().replace('GCAcceleration accel', 'NewAcceleration accel'))
            before = target.read_bytes()
            with self.assertRaises(ValueError): patch.apply(root)
            self.assertEqual(before, target.read_bytes())

    def test_level_gravity_and_rotation_share_a_basis(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = self.fixture(root)
            patch.apply(root)
            text = target.read_text()
            def converted(name, xyz):
                expressions = re.findall(r'data\[\d\] = ([^;]*\b' + name + r'\.[^;]*);', text)
                self.assertEqual(len(expressions), 3)
                values = {name: SimpleNamespace(x=xyz[0], y=xyz[1], z=xyz[2]), 'SDL_STANDARD_GRAVITY': 1.0}
                return tuple(eval(e, {'__builtins__': {}}, values) for e in expressions)
            # Measured level-controller gravity is along Apple's negative Z.
            self.assertEqual(converted('accel', (0, 0, -1)), (0, 1, 0))
            self.assertEqual(converted('rate', (0, 0, 1)), (0, 1, 0))
            # Acceleration's sign convention differs, but its axis rotation
            # must stay identical through pitch, yaw, and roll.
            for vector in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (.2, -.4, .7)):
                self.assertEqual(converted('accel', vector), tuple(-v for v in converted('rate', vector)))
