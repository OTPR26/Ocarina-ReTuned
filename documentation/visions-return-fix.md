# Visions return and layout fixes

Issue #7 also reproduced on Android. When the movie worker exited, the
scheduler returned `Terminated` even though the primary game thread was
waiting. The window loop consequently closed the game.

`apply_native_port.apply_worker_exit()` corrects both scheduler return paths.
A completed worker leaves the process waiting while other threads survive.
Faults remain faults; the final thread exit still ends the process.

The native scheduler regression fails before the fix and passes afterward.
Interpreter and Mac process tests pass, and the Thor owner verified returning
from the same Vision to gameplay. Mac gameplay verification remains pending.

In Single mode, the Visions browser places the normal-sized title and prompt
at the top, choices on the left, the description on the right, and Back at
the bottom left. Videos and their fades use the full screen. Dual mode keeps
its native layout.

The description background and text share one native draw. The title is
submitted separately during the menu update. Its bounds use the order
**top, bottom, left, right**; the size adjustment preserves its center and
texture coordinates. The exact rectangle is checked before modification.

The Thor owner approved the browser and full-screen playback. The clean
module was replayed and visually checked; normal startup was restored and
saves/settings hashes were unchanged. The selected texture pack has no HD
replacement for the native Visions/Back atlas.
