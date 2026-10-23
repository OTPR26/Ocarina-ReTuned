# iOS and Apple TV setup

The unsigned iOS and tvOS downloads do not contain a prepared game. Signing and installing the download alone is not enough to play. Prepare your own supported ROM on a Mac first.

You need a Mac with Xcode, CMake, and Ninja; the Mac Preview; the unsigned IPA for your device; a decrypted **USA Ocarina of Time 3D ROM**; and your own installed signing certificate and provisioning profile. The profile must permit the app identifier and device platform.

1. Extract the Mac Preview. Extract the unsigned IPA into a separate folder; its app is `Payload/OcarinaReTuned.app`.
2. Run the Mac toolkit’s `prepare_apple_app.py` with the paths below. Choose a new, empty work folder and a new output filename. Use `ios` for iPhone/iPad or `tvos` for Apple TV.
3. Install the resulting prepared IPA using your signing/install tool. If it signs the app again, it must retain and sign the embedded frameworks as well.

The preparation command has this form. Replace the example paths with your own; `--identity` is the SHA-1 identifier of your installed certificate, not its password.

```sh
APP="/Applications/Ocarina ReTuned.app"
RESOURCES="$APP/Contents/Resources"
KIT="$RESOURCES/setup"
"$KIT/python/bin/python3" "$KIT/project/tools/native/prepare_apple_app.py" \
  --kit "$KIT/kit.json" \
  --host "$APP/Contents/MacOS/retuned-native" \
  --rom "/path/to/your-game.3ds" \
  --data-root "/path/to/new-apple-work-folder" \
  --template "/path/to/Payload/OcarinaReTuned.app" \
  --provisioning "/path/to/your.mobileprovision" \
  --identity "YOUR_CERTIFICATE_SHA1" \
  --controller-db "$RESOURCES/gamecontrollerdb.txt" \
  --platform ios \
  --output "/path/to/Ocarina-ReTuned-Prepared.ipa"
```

Run the script with `--help` to see all options. Preparation compiles the game for your device and can take several minutes. Keep the resulting IPA private: it contains your game data.

When updating, keep the same app identifier and compatible signing identity. Do not delete the installed app to troubleshoot, because that can remove local saves. The public downloads do not enable iCloud sync.

## Startup messages

- **APPLE-1:** No prepared game was found. Complete Mac preparation first.
- **APPLE-2:** Setup files are incomplete or invalid. Prepare a new IPA.
- **APPLE-3:** The generated game framework is missing. Check that your signing tool retained it.
- **APPLE-4:** Local setup files could not be read or written. Check free storage and restart the app.
- **APPLE-5:** The runtime reported a startup error. Report your device, OS version, signing tool, and whether Mac preparation completed.

A black screen before any message may be a different failure. Include the same details when reporting it; these checks cannot diagnose failures that occur before the app starts.
