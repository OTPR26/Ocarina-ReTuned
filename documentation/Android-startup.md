# Android startup diagnostics

If Ocarina ReTuned closes unexpectedly, open it again. On supported Android versions, a recovery screen offers **Copy report** and **Continue to app**.

You can also open **Startup diagnostics** from first-time setup or the save-file manager. Paste the copied report into your GitHub issue, along with whether the ROM chooser appeared and what you last saw.

The report includes the app version, device model, Android version, memory availability, advertised Vulkan capabilities, last recorded startup stage, and any captured failure. It excludes ROMs, saves, file paths, account identifiers, and exception messages. Nothing is uploaded automatically.

Android 11 and later can report previous native crashes, initialization failures, low-memory exits, and apps that stopped responding. Android 10 can retain Java failures and startup checkpoints, but cannot retrieve previous native exit reasons. An advertised Vulkan version does not establish that the renderer works correctly on that driver.
