# Android startup diagnostics

If Ocarina ReTuned closes unexpectedly, open it again. On supported Android versions, a recovery screen offers **Copy report** and **Continue to app**.

You can also open **Startup diagnostics** from first-time setup or the save-file manager. Paste the copied report into your GitHub issue, along with whether the ROM chooser appeared and what you last saw.

The report includes the app version, device model, Android version, memory availability, advertised Vulkan capabilities, last recorded startup stage, and any captured failure. It excludes ROMs, saves, file paths, account identifiers, and exception messages. Nothing is uploaded automatically.

The next diagnostics build adds native startup checkpoints for module loading,
fonts, guest memory, Vulkan, shader preparation, and guest execution. Each records
system memory availability, process PSS, and native heap usage. Android's exit PSS
and RSS are included when available; these are sampled values, not peak usage.
Available memory shown after reopening is not the memory available at the crash.
The renderer also records its queried Vulkan API, vendor ID, and driver version,
separately from Android's advertised feature values. A caught native exception
marks recovery as pending without exporting its message.

On Android 12 and later, an available native tombstone is reduced to the signal,
up to 12 frames from the crashing thread, module-relative program counters, known
library names, and build IDs. Raw tombstones, absolute addresses, paths, function
names, command lines, messages, and memory contents are not exported. Unknown
libraries are reported as `other native library`. Missing, oversized, or malformed
traces produce a short unavailable message. These diagnostics do not install or
select replacement Vulkan drivers.

Android 11 and later can report previous native crashes, initialization failures, low-memory exits, and apps that stopped responding. Android 10 can retain Java failures and startup checkpoints, but cannot retrieve previous native exit reasons. An advertised Vulkan version does not establish that the renderer works correctly on that driver.
