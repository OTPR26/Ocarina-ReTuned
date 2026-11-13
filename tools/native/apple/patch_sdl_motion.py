"""Expose total acceleration in the same controller basis as the gyro."""
from pathlib import Path
import sys


def apply(root):
    path = Path(root) / 'src/joystick/iphoneos/SDL_mfijoystick.m'
    text = path.read_text()
    replacements = (
        ('if (motion && motion.hasGravityAndUserAcceleration) {\n'
         '                    SDL_PrivateJoystickAddSensor(joystick, SDL_SENSOR_ACCEL, 0.0f);',
         'if (motion) {\n'
         '                    SDL_PrivateJoystickAddSensor(joystick, SDL_SENSOR_ACCEL, 0.0f);'),
        ('if (motion.hasGravityAndUserAcceleration) {\n'
         '                        GCAcceleration accel = motion.acceleration;',
         '/* Total acceleration is available without gravity separation. */\n'
         '                    {\n'
         '                        GCAcceleration accel = motion.acceleration;'),
        ('data[0] = -accel.x * SDL_STANDARD_GRAVITY;\n'
         '                        data[1] = -accel.y * SDL_STANDARD_GRAVITY;\n'
         '                        data[2] = -accel.z * SDL_STANDARD_GRAVITY;',
         '/* Match the rotationRate basis: x, z, -y. */\n'
         '                        data[0] = -accel.x * SDL_STANDARD_GRAVITY;\n'
         '                        data[1] = -accel.z * SDL_STANDARD_GRAVITY;\n'
         '                        data[2] = accel.y * SDL_STANDARD_GRAVITY;'),
    )
    for before, after in replacements:
        if after in text:
            continue
        if text.count(before) != 1:
            raise ValueError('SDL controller-motion context changed')
        text = text.replace(before, after)
    path.write_text(text)


if __name__ == '__main__':
    apply(sys.argv[1])
