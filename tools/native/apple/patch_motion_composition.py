"""Keep stick yaw from rotating the controller's pitch axis."""
from pathlib import Path


def apply(engine):
    path = Path(engine) / 'tools/three_ds/input/three_ds_motion_composition.cpp'
    text = path.read_text()
    before = '''    const auto baseDown = Unit(base);
    const Vector yawAxis{-baseDown[0]*yawRate, -baseDown[1]*yawRate, -baseDown[2]*yawRate};
    // Local pitch acts on the left, world-up yaw on the right. This factorization
    // preserves gravity under yaw even when both controls move in the same step.
    const auto step = [&](double t) {
        return Normalize(Multiply(Multiply(Delta({pitchRate,0,0}, t), next.SensorToVirtual), Delta(yawAxis, t)));
    };'''
    after = '''    // Stick yaw is an angular velocity, not a change to the sensor basis.
    // Accumulating it here rotates physical pitch into roll after turning.
    // Only virtual pitch must persist to retain the aimed gravity vector.
    const auto step = [&](double t) {
        return Normalize(Multiply(Delta({pitchRate,0,0}, t), next.SensorToVirtual));
    };'''
    if after in text:
        return
    if text.count(before) != 1:
        raise ValueError('Motion composition context changed')
    path.write_text(text.replace(before, after))
