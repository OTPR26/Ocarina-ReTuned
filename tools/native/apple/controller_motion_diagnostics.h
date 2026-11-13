// Private device tests opt in at launch; normal gameplay emits no sensor logs.
#pragma once
#include <SDL.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static void RetunedControllerMotionDiagnostics() {
    static const bool enabled = [] {
        const char* value = std::getenv("RETUNED_MOTION_DIAGNOSTICS");
        return value && std::strcmp(value, "1") == 0;
    }();
    if (!enabled) return;
    static Uint64 next = 0;
    const Uint64 now = SDL_GetTicks64();
    if (now < next) return;
    next = now + 2000;
    std::fprintf(stderr, "RETUNED_MOTION controllers=%lu sdl_devices=%d\n",
        (unsigned long)GCController.controllers.count, SDL_NumJoysticks());
    unsigned index = 0;
    for (GCController* controller in GCController.controllers) {
        GCMotion* motion = controller.motion;
        const GCRotationRate rate = motion ? motion.rotationRate : GCRotationRate{};
        const GCAcceleration accel = motion ? motion.acceleration : GCAcceleration{};
        std::fprintf(stderr,
            "RETUNED_MOTION apple_index=%u gamepad=%d motion=%d gyro=%d separated_gravity=%d active=%d manual_activation=%d rate=%.4f,%.4f,%.4f accel=%.4f,%.4f,%.4f\n",
            index++, controller.extendedGamepad != nil, motion != nil,
            motion.hasRotationRate, motion.hasGravityAndUserAcceleration,
            motion.sensorsActive, motion.sensorsRequireManualActivation,
            rate.x, rate.y, rate.z, accel.x, accel.y, accel.z);
    }
    for (int i = 0; i < SDL_NumJoysticks(); ++i) {
        SDL_GameController* pad = SDL_GameControllerFromInstanceID(SDL_JoystickGetDeviceInstanceID(i));
        if (!pad) continue;
        float gyro[3]{}, accel[3]{};
        const int gyroResult = SDL_GameControllerGetSensorData(pad, SDL_SENSOR_GYRO, gyro, 3);
        const int accelResult = SDL_GameControllerGetSensorData(pad, SDL_SENSOR_ACCEL, accel, 3);
        std::fprintf(stderr,
            "RETUNED_MOTION sdl_index=%d gyro_enabled=%d accel_enabled=%d gyro_result=%d accel_result=%d rate=%.4f,%.4f,%.4f accel=%.4f,%.4f,%.4f\n",
            i, SDL_GameControllerIsSensorEnabled(pad, SDL_SENSOR_GYRO),
            SDL_GameControllerIsSensorEnabled(pad, SDL_SENSOR_ACCEL), gyroResult, accelResult,
            gyro[0], gyro[1], gyro[2], accel[0], accel[1], accel[2]);
    }
}
