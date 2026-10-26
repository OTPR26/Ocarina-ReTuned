# Manual jump

Quality of life → Manual jump offers **Off**, **ZR**, and **X**. Off is the
default. Choosing X moves its equipped item to ZR during gameplay. Menus and
normal ledge jumps keep their existing controls; save files and item
assignments are unchanged.

A fresh press starts the native jump action while Link is grounded and idle
or moving. Carried actors, Iron Boots, cutscenes, menus, and configuration
chords prevent jumping. Holding the button does not queue another jump.
The native jump routine uses a hard-float calling convention, which the
wrapper declares explicitly.

In X mode, the physical HUD uses the ReMasked shoulder artwork beside the
remaining three-button group. Touch controls follow the same mapping and
move the equipped item and ammo to ZR. Shoulders are smaller and unlabelled;
gameplay buttons have transparent centers. Settings and Start retain their
filled backgrounds.

ImGui navigation is disabled during gameplay, and any pending window-switch
overlay is cleared. Controller navigation remains available in menus.

Older prepared games omit the manual-jump capability, so the setting stays
hidden until their game module is updated. Local tests cover input edges,
item remapping, native eligibility, HUD geometry, and staging. The Thor owner
verified jumping and the touch ZR item mapping. Release-kit integration and
platform package validation remain separate release checks.
