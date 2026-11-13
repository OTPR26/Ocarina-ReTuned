# Touch controls

Turn on **Settings → Touch → Show touch controls** to display the controller overlay. The eye button temporarily hides or restores it. Turning the setting off also hides the eye.

## Layout editor

On Android and iOS, **Edit touch layout** lets you drag buttons, the D-pad, and both stick regions to new positions, and pinch or spread two fingers to resize a control. The selected control shows its size percentage. The game remains paused in Settings while you edit.

- **Save** keeps the new positions and sizes.
- **Cancel** or Android Back discards unsaved changes.
- **Reset** restores the default positions and sizes; choose Save to keep the reset.

Single-screen and dual-screen layouts are stored separately. Positions adapt to the display size, and controls stay inside the safe screen area. Control size and opacity remain in Touch settings. Hidden shoulder controls appear in the editor so you can position them before enabling them.

Moving an item button also moves its item icon and touch target. A moved floating stick starts within its displayed region; an unmoved floating stick retains its larger default touch area.

## Minimap

The folded-map button toggles the minimap without requiring ZL or ZR to be displayed. It can be moved in the layout editor. Hiding the minimap uses the game's existing hold gesture, so it takes a few seconds. The Map button remains available when the minimap is hidden.

## Sizes and shoulder labels

In **Edit touch layout**, pinch a control to resize it from 50% to 150%. This multiplies the overall Control size setting. The D-pad resizes as one group; buttons, Move, and Look can each be resized independently. Their touch targets and item artwork follow the new size. Sizes are saved separately for single-screen and dual-screen layouts.

**Shoulder labels** adds L, R, ZL, and ZR to the visible shoulder buttons. It does not enable hidden shoulders or change their assignments. Labels remain off by default.

## Drag to look

**Drag to look** replaces the Look stick with swiping across the right side of the screen. Camera movement stops when the swipe stops or the finger lifts. Buttons take priority over the camera region, so movement and button presses can be used alongside camera swipes. The saved Look-stick position remains available when drag-to-look is turned off.

The existing stick mode, unlabelled shoulders, and 100% individual sizes remain the defaults.

## Controller motion

Android 12 and newer can use motion sensors exposed by a connected controller's firmware. Controllers with their own SDL motion support keep that path. Otherwise, ReTuned looks for an unambiguous match to the selected controller, including a separate motion-sensor device matched to the selected controller. Unsupported devices retain device-motion aiming. Controller samples expire after 250 ms, and sensor listeners stop when the app loses focus or closes.

Android controller motion has been tested on the Odin 2 Portal with a Nintendo Switch Pro Controller. iOS uses the shared Apple controller-motion implementation tested on tvOS; an iPhone Bluetooth-controller playtest is still pending. Support depends on the operating system exposing the controller’s sensors; not every Bluetooth controller provides motion data.
