    // Switch shoulders are digital, but SDL exposes them as trigger axes.
    // Exercise both endpoints independently and together, including releases.
    for (const unsigned shoulders : {0U, 1U, 1U, 0U, 2U, 2U, 3U, 1U, 0U}) {
        SDL_JoystickSetVirtualAxis(joystick, SDL_CONTROLLER_AXIS_TRIGGERLEFT,
                                  shoulders & 1U ? 32767 : -32768);
        SDL_JoystickSetVirtualAxis(joystick, SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
                                  shoulders & 2U ? 32767 : -32768);
        SDL_GameControllerUpdate();
        Require(IsSdlControllerButtonHeld(controller, GamepadButton::LeftTrigger, 6000) ==
                    bool(shoulders & 1U) &&
                IsSdlControllerButtonHeld(controller, GamepadButton::RightTrigger, 6000) ==
                    bool(shoulders & 2U),
                "digital ZL/ZR axes remain independent through holds and releases");
    }
