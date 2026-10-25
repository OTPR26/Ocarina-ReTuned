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

The audited local toolchain reports Xcode 27.0 and the iOS 27.0 SDK. No available Duo simulator was listed. Duo-specific API availability and the required SDK/simulator must be verified before implementation; do not claim Duo testing based on an ordinary iPhone simulator.

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
