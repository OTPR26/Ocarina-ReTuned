# Optional dual-screen support: code audit and implementation plan

Audit date: 2026-10-25. This is a source audit and proposed design, not implemented support or a hardware test.

## Required behavior

Android offers **Single Screen** and **Dual Screen**. iPhone Duo offers **Single Screen**, **Dual Screen**, and **Hybrid**. Keep Single Screen as the default.

| Selection | Behavior |
| --- | --- |
| Single Screen | Retain ReFramed's single-screen interface. Adapt gameplay, menus, dialogue, HUD, and touch controls to the available window dimensions and safe areas. Unfolding a Duo must not enable the lower game screen. |
| Dual Screen | Show the game's top and lower interfaces in separate views. On a compatible Android handheld, route them to its two displays; on Duo, arrange them within the inner display. Keep image proportions and map touch only to the appropriate content region. |
| Hybrid — iPhone Duo only | Use Single Screen normally. Switch to Dual Screen in the laptop-style fold, then return to Single Screen when opened flat or closed. Do not treat every partial fold or rotation as laptop posture. |

Separate the saved selection from the effective layout. If a second display becomes unavailable, fall back safely without overwriting the user's preference. Switching must not reset the running game, audio, saves, or controller bindings. Reject touches in letterbox margins and the fold, and release held touch inputs during transitions.

## What remains in the code

The original lower-screen machinery was not completely removed:

- The pinned runtime retains `NativeA32CtrHostServices::BottomFramebuffer()`, bottom-framebuffer tracking, GPU display transfers, and presentation snapshots.
- It retains `NativeLowerScreen320x240` input mapping and native touch coordinates.
- The existing bottom-screen presentation branch is a frontend substitution path, not a simultaneous second game view. `ShouldPresentNativeBottomFrontend()` enables it only for the `oot3d` profile during a native frontend phase. ReTuned uses `reframed`.
- ReFramed has separately published Single Screen and Dual Screen sources. Its 2.0.2 source README says Dual Screen is unchanged from 2.0.1; the two-screen edition retains the traditional two-screen arrangement with ReFramed additions.

The previously cited `kPauseLowerScreenBlock` skip is guarded by the runtime's `TopScreenUiProfile`. Window setup sets that flag only for `topscreen`, not `reframed`. It is not evidence that ReTuned's ReFramed mode disables that block.

## Gaps and affected code

| Area | Evidence | Needed work |
| --- | --- | --- |
| Prepared game | `resources/source-pins.json` selects `release-source/2.0.2/single`. The current mod uses `SingleScreen_DrawSecondaryCallback()` and `SingleScreen_AfterTopPass()` to replay lower-screen UI onto the top pass. | Compare the accepted Dual Screen patch set with the current Single Screen changes. Make presentation behavior switchable without losing camera, HUD, QoL, fonts, or current fixes. Merely exposing another framebuffer cannot undo relocated UI. |
| Runtime presentation | `oot3d_native_a32_window_frame.cpp` selects top scanout and optionally substitutes a bottom frontend into the host presentation. | Expose top and bottom outputs independently; compose both in one window first, then support a second platform surface. Check GPU-rendered and CPU-written lower-screen content. |
| Input | The runtime maps a pointer using the host window dimensions; `tools/frontend/touch_overlay.h` uses the main ImGui viewport. | Give each view explicit content bounds, screen identity, orientation, and touch ownership. Map lower-view touches to native 320×240 coordinates, independently of virtual controller touches. |
| HUD on touch buttons | `TouchHudActive` and its anchors assume one gameplay viewport. | Anchor item icons to the view containing the virtual buttons. Avoid duplicate or displaced HUD elements in dual mode. Preserve the existing single-screen feature. |
| Settings and capabilities | `tools/frontend/reframed_settings.h` bridges nine existing ReFramed options. There is no screen-mode capability or setting. | Add a separate host screen-mode setting and a versioned prepared-game capability. Do not repurpose `UiProfile=oot3d`, which would bypass ReFramed integration. |
| Android host | `RetunedGameActivity` creates one SDL surface and one `TouchOverlay`; there is no display listener or second-display owner. | Add display discovery, lifecycle handling, output selection, and a rendering surface for the second display. Verify the Thor's actual display topology rather than assuming all foldables expose two logical displays. |
| iPhone Duo host | The Apple bundle declares landscape orientations only. UIKit/SDL patches manage one game window, and there is no fold-aware layout or posture bridge. | Implement two logical game views within the inner window, adaptive single-screen sizing, relevant orientations, safe/fold regions, and Hybrid posture handling. Multiple app instances or an external-display scene are not prerequisites for this layout. |
| Preparation and upgrades | The toolkit provides one mod image and exports selected symbols into its manifest; older data can lack newer metadata. | Version capabilities, validate before enabling modes, and provide a safe migration or explicit preparation step. Never silently enable an unsupported mode or overwrite progress. |

The relevant upstream runtime files above are under `tools/oot3d/native_game_runtime/`, except `ShouldPresentNativeBottomFrontend()`, which is in `tools/oot3d/ui_topscreen/oot3d_top_screen_mod_profile.cpp`. The runtime revision is recorded in `resources/source-pins.json`. Local platform builds use patched copies of that baseline, so an unpatched reference alone does not establish final app behavior.

## Recommended implementation sequence

1. **Prove both game outputs in one diagnostic window.** Use the accepted ReFramed Dual Screen source as a behavioral reference. Check live lower-screen inventory, map, ocarina, file selection, naming, dialogue, visions, and Game Over. This isolates game/rendering defects from device routing.
2. **Unify presentation behavior in the prepared mod.** Add a host-controlled presentation mode and a versioned manifest bridge. Keep one running guest process. A temporary separate Dual Screen prepared image is useful for comparison, but choosing between separately compiled games at launch does not satisfy Hybrid.
3. **Implement shared view composition and input.** Produce two output views from one simulation, with explicit content rectangles and shared GPU resources. Avoid full-frame GPU-to-CPU readback and avoid a second game/audio instance. Add adaptive Single Screen layout as part of this work, not as a later Duo fallback.
4. **Add manual Android dual-screen routing.** Start with the actual Thor topology, then test display removal, rotation, suspend/resume, and touch/controller interaction. Single-display devices retain a safe single-screen mode.
5. **Add Duo manual modes, then Hybrid.** Bind Apple layout/fold information into the shared layout model. Hybrid needs a posture decision using hinge state, orientation, and layout regions; hinge angle alone cannot distinguish laptop from book posture. Use separate entry/exit conditions to avoid rapid switching. Commit transitions at a safe game/render boundary and queue them if a menu transaction cannot yet transition safely.
6. **Validate compatibility and upgrade behavior before release.** Existing saves remain shared between modes. Modes must not require separate apps or repeated ROM preparation every time they are selected. Existing prepared data may need a one-time compatible upgrade when introducing the new mod capability; the exact migration depends on the final patch changes.

Prefer a gradual internal rollout: render proof, manual modes, then Hybrid. Do not expose Hybrid publicly until live transitions work during gameplay and the native lower-screen menus.

## Platform research and local limits

Android provides display discovery/listeners and presentation-display APIs. Device-specific display and touch behavior still requires a hardware check. See [DisplayManager](https://developer.android.com/reference/android/hardware/display/DisplayManager) and [connected-display guidance](https://developer.android.com/develop/adaptive-apps/guides/support-connected-displays).

For Duo, Apple's guidance covers adaptive inner/outer window sizes and reserved fold/camera regions. The UIKit hinge API reports discrete state and angle, while layout APIs define usable regions. These are inputs to our Hybrid policy, not an existing ReTuned implementation. See [preparing for Duo](https://developer.apple.com/iphone-duo/prepare/), [adaptive layouts](https://developer.apple.com/videos/play/tech-talks/111463/), and [hinge observation](https://developer.apple.com/videos/play/tech-talks/111464/).

The project now uses the installed Xcode 27.1 and iOS 27.1 SDK through an explicit `DEVELOPER_DIR`. The iOS 27.1 runtime and a dedicated Duo simulator are installed. The older Xcode beta remains available for other projects; the global toolchain selection was not changed.

## Acceptance checks

- Single Screen remains appropriate on ordinary phones, the closed Duo, and the unfolded Duo; no forced dual mode, stretched UI, or fixed phone-sized canvas.
- Top and lower views display independent, current content, with correct aspect ratio, orientation, fonts, textures, and clipping.
- Touching lower-screen inventory and map controls reaches the correct native coordinates; margins, hinge regions, and the upper view do not generate false touches.
- HUD-on-buttons follows the selected layout and preserves controller operation.
- Hybrid switches only in the intended laptop posture and returns cleanly; save progress, camera, audio, settings, and held input remain correct.
- Disconnecting a display, folding, rotating, opening Settings, and resuming the app do not crash or restart the game.
- Existing prepared games either migrate safely or receive a precise compatibility message. No reinstall, signing-channel change, save replacement, or silent ROM-preparation loop.
- Profile memory and frame time with both views and the mobile texture pack. Allocate lower-screen rendering only when needed; do not assume two views imply two world renders.

No apps, prepared games, release assets, or GitHub resources were changed by this audit. No GitHub Actions were run.

## First implementation stage

An opt-in Mac/NRI rendering proof now lives in `tools/frontend/apply_screen_probe.py`, with shared layout and coordinate mapping in `screen_layout.h` and `screen_probe.h`. It is not invoked by normal packaging or exposed as a released setting.

The proof composes top and lower GPU snapshots in one window, using `RETUNED_SCREEN_PROBE=stacked` or `side-by-side`. Native top-target resolution and projection use the top pane's dimensions; the lower scanout preserves the top image. Both views share one guest process, and the native input route maps only the lower content rectangle to 320×240. The gap scales consistently between logical window points and drawable pixels.

Validation uses an isolated profile, copied saves, and the original native two-screen layout as a renderer baseline. It does not yet establish ReFramed Dual Screen integration, native Android display routing, iPhone Duo layout, or Hybrid transitions. Physical pointer/touchscreen testing is also separate from the layout tests and scripted native touch-input checks.

The C++ checks cover both arrangements, margins, native coordinate bounds, Single Screen with no lower touch region, invalid dimensions, Retina scale invariance, default-off behavior, and restoring the top scanout scope after a rendering exception. To run them after applying the proof to a local runtime checkout:

```sh
clang++ -std=c++20 -I tools/frontend tests/screen_layout.cpp -o /tmp/retuned-screen-layout-check
/tmp/retuned-screen-layout-check
python3 tools/frontend/apply_screen_probe.py /path/to/local/runtime
clang++ -std=c++20 -I /path/to/local/runtime/runtime/three_ds_recomp/include/fast/oot3d tests/screen_probe.cpp -o /tmp/retuned-screen-probe-check
/tmp/retuned-screen-probe-check
```

Any runtime test must use an explicit `--launch-profile` pointing to isolated data. The probe is not an upgrade path for an existing prepared game.

## ReFramed live-switch experiment

The next private experiment adds a frame-boundary handshake between the host
and one switchable ReFramed module. `apply_screen_presentation.py` instruments
an isolated canonical native mod source; `apply_reframed_screen_probe.py`
connects it to the opt-in renderer. Neither applier runs in release staging.

The native preparer normalizes supported input to its canonical EUR-addressed
image. This experiment therefore builds the matching EUR-addressed mod, even
when the user's source cartridge is USA. Selecting a mod by the input ROM's
label alone produces incorrect native call targets; translation closure must
pass before a test can run.

The prepared manifest advertises `reframed_frontend.presentation` schema 1
only when both mode-query and mode-request functions exist and are valid ARM
functions. Existing modules advertise no capability. The host follows the
guest's acknowledged mode, retries a busy request, and stops the isolated
test if execution or acknowledgement fails. It releases the current pointer
sample when changing the view layout. The mod currently accepts transitions
only outside file selection, dialogue, pause/menu transitions, ocarina, and
Game Over. A pending choice does not alter rendering or saved preferences.

A local test loaded a copied save into the Temple of Time and switched
Single → Dual at guest frame 633, then Dual → Single at frame 847 in the same
process. Captures show the independent lower map/items/health interface in
Dual and the restored ReFramed HUD in Single. It completed 2,600 host frames
and exited successfully. This establishes a gameplay switching proof, not
complete Dual Screen support: all native menus, held-touch transitions,
dialogue, audio continuity, and long sessions still require validation.
Android output routing and playable Duo Single/Dual/Hybrid integration remain unimplemented.

Host checks cover invalid/absent capabilities, deferred changes, invalid
mode requests, guest execution failures, and a false acknowledgement. The C
mode protocol and C++ handshake pass AddressSanitizer/UndefinedBehaviorSanitizer
checks; the ARM mod, native host, and translated title module build locally.

## Duo SDK and layout proof

The owner-authorized Xcode update is complete, including first-launch components
and the iOS 27.1 simulator runtime. `duo_layout_observer.mm` reads UIKit hinge
updates, safe bounds, division strips, and active occlusions. New UIKit symbols
are weak linked, and the observer also compiles with the older SDK fallback.

The standalone `tests/apple/build_duo_probe.py` diagnostic uses no game data.
On a dedicated Duo simulator, Single expanded from the outer to the inner
display without enabling Dual. Manual Dual arranged two aspect-correct panes
around Apple's division strip; rotating a partially folded device changed
from side-by-side to stacked panes. Closing fell back to Single, and reopening
restored the selected Dual mode without restarting the diagnostic. An actual
lower-pane tap mapped to native coordinate 160,120; an upper-pane tap was rejected.
These checks validate layout and input routing in the diagnostic, not gameplay.

The shared mode policy preserves the user's preference through fallbacks,
requires a compatible prepared-game capability, and debounces a confirmed
laptop-posture signal. Hybrid remains disabled in the diagnostic: the simulator
reports no device-motion data, and hinge angle or a horizontal divider alone
does not prove laptop posture. Physical posture classification, live game
integration, and native-menu transition validation remain unfinished.

Build the isolated diagnostic with:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
python3 tests/apple/build_duo_probe.py /path/to/OcarinaDisplayProbe.app
```

No installed game apps or real saves were changed by these experiments, and
no GitHub Actions were used.

## Playable Duo host integration experiment

The opt-in `tools/native/apple/apply_duo_game_probe.py` connects the UIKit
observer to the SDL game window. Single and Dual selections request a mode
through the prepared-game handshake. Rendering follows the acknowledged mode;
layout changes release the current touch sample and refresh scene projection.
The same safe-area/division geometry supplies drawable-pixel composition and
logical-point lower-screen touch mapping. Closed or unavailable lower views
reject lower touches. Hybrid remains unavailable.

The private Apple simulator host and matching translated module compile and
link. Device-target compilation of the UIKit/SDL adapter also passes. This is
not yet a successful Duo gameplay test: Apple's simulator GPU advertises a
32-byte render-target budget and lacks `VK_FORMAT_R32_UINT` storage-image
atomics. Skipping the optional, disabled grass initializer in this simulator
experiment gets past its eager 44/52-byte pipelines, but the required image
atomic capability still stops native game presentation. GPU validation was
not disabled. Physical-device rendering is unchanged by the simulator-only
workaround.

The shared game was tested separately on the Mac GPU with copied saves, including
a replay of the Duo simulator's measured fold geometry. This is not native Duo
execution. Native
Dual Items, Gear, Map, and the Ocarina song list render. Native-coordinate
item selection changes the item description, and lower-screen tab touches
change Gear/Map/Items correctly. The experiment now bypasses the single-screen
400x240 shell transform for native Dual touches. A mode change requested while
Items was open remained deferred until the menu closed, then returned to
Single in the same process.

The experiment is excluded from normal package staging. File selection,
naming, Save/Game Over, physical touch/controller input, suspend/resume,
long-session audio continuity, and complete native Duo gameplay remain open
validation items. Existing prepared data does not gain this capability without
a compatible mod/module preparation. No release or installed user app was
changed.

The Apple host must be configured with `OOT3D_DIRECT_AOT_PLUGIN=ON` and
`OOT3D_WHOLE_AOT_PRODUCT_MODE=ON`, the matching simulator/device MoltenVK
library, and the correct SDK. The private diagnostic uses
`RETUNED_SCREEN_PROBE=duo`; no normal build enables it implicitly. The simulator
run used the Authentic graphics preset. Its UIKit Single/Dual selector is a
private test control, not the final saved Settings interface.

## Dual-screen sidebar buttons

The experimental Dual presentation uses icon-only side buttons, matching
ReMasked's removal of native controller labels. The canonical gameplay and
Items sidebar each have a dedicated four-glyph draw for X, Y, I, and II;
`dual_screen_sidebar.c` skips only those draws in Dual. Single retains the
native labels. Equipped-item renderers, quantity renderers, button artwork,
transition alpha, and native touch handling are unchanged. The separate sword
B badge is collapsed only during gameplay submission, then its source geometry
is restored immediately. No shared atlas pixels are erased.

## Android physical-display experiment

`tools/native/android/apply_dual_screen_probe.py` is an opt-in integration for
an otherwise prepared Android engine. It is excluded from release staging.
The matching prepared mod/module is required; updating only the APK does not
add native Dual capability to an older prepared game.

On the Thor, Android exposes the lower internal panel as a separate display,
not as a presentation-category display. A nonfocusable Android Presentation
owns its SurfaceView. The renderer presents native lower scanout through a
second Vulkan swapchain on the same graphics device/queue, without CPU image
copying or a second guest update. Native lower-screen touch uses the same
aspect-fitted 320x240 viewport as rendering. Removing a surface releases its
held touch sample. The private probe serializes GPU completion before lower
presentation; optimized scheduling is still future work.

General settings contains a saved Single/Dual screen preference. There is no
floating mode button. Changes wait for the existing safe guest handshake;
selecting Single keeps the lower display until any active menu transition
finishes. An unavailable second display falls back to Single while preserving
the selection. The ReFramed HUD remains on the top screen in Dual and follows
the normal HUD visibility setting.

The Android top view uses the full main display and supplies those dimensions
to scene projection, rather than fitting it back into the original 5:3 frame.
The lower view retains its native 4:3 proportions. Its rotated 240x320 and
480x320 render targets scale to the lower SurfaceView's fitted pixel dimensions;
the latter retains its two-sample display transfer. This allows high-resolution
custom textures to survive lower-screen composition instead of being reduced
to the original render-target resolution. Unrelated targets are unchanged.
Sanitized coordinate tests cover Thor, wide external outputs, both native
sampling ratios, and unavailable displays.

The lower swapchain needs the native renderer's color and depth attachments.
Identity pre-transform matches the main Android output. A compositor reporting
SUBOPTIMAL without a changed surface is not a reason to rebuild identical
buffers every frame. Raw native-window dimensions and swapchain extents are
tracked separately because Android display rotation can make them differ.

Private Thor testing has verified two physical outputs, upright lower
rendering, native lower-screen touch, icon-only side buttons, and copied
in-game saves. The final General preference, top-HUD, and swapchain-stability
checks are recorded separately in private receipts. Suspend/resume, display
loss/reconnection, long-session audio/performance, all menu transitions, and
the final release preparation flow still need coverage. This is a hardware
test build, not a published Android dual-screen release.
