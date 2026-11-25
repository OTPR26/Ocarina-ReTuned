# Apple foreground rendering

The November 16, 2026 Forever Tel Aviv log (tvOS build 0.6.5/19)
ended during startup with `VK_ERROR_DEVICE_LOST` after Metal reported
`kIOGPUCommandBufferCallbackErrorBackgroundExecutionNotPermitted`.
This proves a background GPU denial, but not what caused the foreground
transition. No matching Ocarina crash or memory-limit termination report
was present in the device records inspected.

The SDL scene adapter scheduled synchronous game startup from scene connection,
which can precede scene activation. The renderer lifecycle watch is installed
later, after renderer initialization. Thus an early transition can be missed.

The adapter now defers `postFinishLaunch` until UIApplication is active.
At the end of SDL's UIKit event pump, after both default and tracking run-loop
passes, it keeps servicing UIKit while inactive instead of returning to a
render caller. This covers startup and nested event pumps as well as the normal
frame loop. The existing synchronous renderer pause drains CPU render work,
presents and GPU work before the resign callback returns. A did-background
event also pauses the gate if the earlier will-background event was missed.
The resume path retains its swapchain refresh and pacing-deadline reset.

A previous log containing the specific background-denial diagnostic removes
only the stale `.launching` marker before opening the next log. That failure
must not reset the user's graphics settings as if they caused a startup crash.
Other failures still use the normal safe-presentation fallback. Saves and
controller/motion configuration are not changed by this migration.

Regression checks exercise the actual patched SDL event pump with mocked UIKit
transitions, patch idempotence, duplicate/missed pause events, and the narrow
settings-marker migration. Apple motion composition and tvOS save-recovery
checks remain required. Real TV startup and background/resume verification
requires the owner's permission to launch and leave the app; do not infer
on-device success from these checks. Genuine Vulkan device loss remains fatal;
the patch prevents inactive submissions rather than ignoring GPU errors.
