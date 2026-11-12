# Windows portable mode

Available in Windows Preview 0.6.7. Data migration, folder relocation, and
gameplay have been tested on Windows x64. ARM64 gameplay remains unverified.

Before starting gameplay, open **Settings → General → Portable mode** and choose
**Enable portable mode**. Close other copies of Ocarina ReTuned first.

The app closes, copies and verifies its data, then restarts using a `user` folder
beside the executable. Saves, settings, prepared game files, models, and textures
stored inside the original data folder are copied. The original AppData folder
is retained. An existing `user` folder is never overwritten.

The destination needs enough free space for a full copy and must be writable.
The migration window stays visible while copying and checking files. If migration
fails, the app returns to its original data.

Move the entire app folder, including `user` and `setup`, to move the portable
installation. The app repairs internal paths on its next launch. Texture folders
selected elsewhere on the computer remain external and must be moved or selected
separately. Linked folders are not copied automatically.

When updating, replace the application files while retaining `user`. Do not copy
an older AppData folder over portable saves: the two copies do not synchronize.
