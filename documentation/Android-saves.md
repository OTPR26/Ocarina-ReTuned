# Android saves

Open **Settings → Saves** from the startup screen. Save-file changes are available before gameplay; save and reopen the app first if you are already playing.

## Import and export

- **Import saves:** choose expanded Ocarina of Time 3D USA in-game saves exported from Citra or Azahar: `save00.bin`–`save05.bin` and, optionally, `system.dat`. You can select individual files or a ZIP containing them. Confirm to replace matching files; other slots are kept.
- **Export saves:** choose where to write a ZIP containing the ordinary save files. Extract it before importing into an emulator that expects individual files.

Emulator save states and whole emulator backups are not supported. The app validates filenames and sizes; this does not convert another region’s saves or repair damaged saves. Previous app saves are retained locally when an import replaces them.

## Custom folder and Syncthing

Choose **Custom save folder**, then create or select a dedicated folder such as **Documents/ReTuned Saves** using Android’s folder picker. Grant access when prompted. This folder is outside `Android/data` and can also be selected in Syncthing. No all-files permission is required.

The app loads folder changes before gameplay and copies completed in-game saves back automatically. It keeps an app-local working copy so interrupted folder access does not erase your saves. Let Syncthing finish before opening the game, and play on one synced device at a time.

If both copies change, the app stops syncing and asks you to choose **Use folder saves** or **Keep app saves**. Review which device has the newest progress before resolving. Syncthing conflict files must be resolved first. If access is revoked, select the folder again or choose **Use app save folder**; disconnecting leaves both copies in place.
