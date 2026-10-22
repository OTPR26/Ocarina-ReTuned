# Ocarina ReTuned

A native, single-screen Recomp of Ocarina of Time 3D for Windows, Mac, Linux, Android, iOS and Apple TV. Ocarina ReTuned is a substantially modified fork of TriAevum, integrating Ocarina ReFramed gameplay with its own interface, ROM-preparation flow and platform support.


**The first Preview is available.** Expect rough edges and share feedback about your device, controller and graphics settings.

[Download the Preview](https://github.com/OTPR26/Ocarina-ReTuned/releases/tag/v0.1.0-preview) · [Report an issue](https://github.com/OTPR26/Ocarina-ReTuned/issues)

## Features

- Single-screen gameplay with the Ocarina ReFramed HUD, menus and camera controls.
- A shared startup screen and settings menus, with controller navigation and Apple TV remote support.
- Adjustable internal resolution and frame-rate interpolation, including 60 FPS.
- Bundled HD dialogue fonts with Regular and Bold styles.
- Custom texture-pack support, with memory budgets suited to each device.
- Touch controls on iOS and Android, plus configurable controller bindings.
- iCloud save-sync support in separately configured Apple builds. Sync is off in the downloadable Preview packages.

## How ReTuned differs from TriAevum

TriAevum provides the runtime and translation foundation. ReTuned adds substantial work across the startup and settings interface, controller and touch input, Apple platforms, Android on-device ROM preparation, portable Windows preparation tools, texture-memory management and dialogue rendering.

We also changed what is distributed:

- **Replacement dialogue fonts:** ReTuned Dialogue provides our adapted Regular and Bold font set, based on Liberation Sans under the SIL Open Font License. It replaces reliance on the previous external HD font pack; its source attribution and license are included.
- **Locally generated shaders:** the upstream embedded title-specific GLSL tables and precompiled SPIR-V pack were removed. The generic shader decompiler instead processes data from the user's game locally.
- **Local game preparation:** ROMs and generated game modules are not bundled in the downloads. Users prepare their own supported ROM locally.

Retained runtime components and the included ReFramed/Project Restoration-derived UI resources keep their original licenses and attribution notices.

## What you need

Supply your own legally obtained, supported **decrypted USA Ocarina of Time 3D ROM** in `.3ds` or `.cci` format. Other regions and revisions are not currently supported.

The downloads do not include a ROM, a prepared game module or saves. First-run preparation uses your ROM locally and can take a while. Optional texture packs are supplied separately.

## Downloads and installation

Choose the download for your platform from the [Preview release](https://github.com/OTPR26/Ocarina-ReTuned/releases/tag/v0.1.0-preview). Installation instructions and SHA-256 checksums are included on the release page.

| Platform | Download | Requirements and setup |
| --- | --- | --- |
| Windows x64 | `Ocarina-ReTuned-Preview-Windows-x64.zip` | Extract and run `OcarinaReTuned.exe`. Compiler and preparation tools are included: select your ROM and wait for preparation to finish. |
| Mac | `Ocarina-ReTuned-Preview-Mac.zip` | Apple silicon, macOS 15 or later. Extract `Ocarina ReTuned.app`. ROM preparation requires Apple C++ command-line tools, CMake and Ninja. The app is ad-hoc signed and is not notarized. |
| Linux x86_64 | `Ocarina-ReTuned-Preview-Linux-x86_64.tar.gz` | Extract and run `Ocarina-ReTuned.sh`. Requires glibc 2.38 or later, system graphics drivers, CMake 3.30 or later, Ninja and a C++20 compiler with system headers. Audio uses your desktop audio session. |
| Android ARM64 | `Ocarina-ReTuned-Preview-Android-arm64.apk` | Install the APK and select your ROM. Preparation runs entirely on the device; no desktop companion is needed. |
| iOS | `Ocarina-ReTuned-Preview-iOS-Unsigned.ipa` | Unsigned; requires ROM preparation and signing on a Mac before installation. See below. |
| tvOS | `Ocarina-ReTuned-Preview-tvOS-Unsigned.ipa` | Unsigned; requires ROM preparation and signing on a Mac before installation. See below. |

### iOS and Apple TV

The unsigned Apple downloads require **a Mac with Xcode, your supported ROM, and your own compatible signing identity and provisioning profile**. Signing the downloaded IPA alone is not enough; the game must be prepared first.

The Mac app includes the preparation toolkit. Unpack the unsigned IPA and use `prepare_apple_app.py` from:

```text
Ocarina ReTuned.app/Contents/Resources/setup/project/tools/native/
```

Run the script with `--help` for its required inputs. The Mac app supplies the preparation kit, host and controller database. Prepare, sign and install the resulting app locally. The prepared IPA contains your game data and must not be redistributed.

**iCloud sync is off in these downloads.** Enabling it requires a source build configured for a compatible iCloud container and provisioning profile; signing alone does not enable sync.

## Fonts, textures and controls

Choose **Settings > HUD > Dialogue font** to switch between Regular and Bold. Restart the app to apply the change.

HD dialogue fonts are included. They do not replace world textures or every image-based title and label in the game. Higher-resolution world textures require a separate texture pack.

Startup and settings support controller navigation. On Apple TV, Back on the remote or B on a controller returns from a settings page to the category list. On desktop, the mouse remains free by default; explicit keyboard-and-mouse capture is available.

## Preview limitations

- High resolutions, interpolated frame rates and large texture packs depend on your hardware. Texture-memory limits can leave some textures at their original resolution, especially on Apple TV.
- First preparation can take a long time, particularly on slower devices.
- Font-style changes require an app restart.
- Mac and Linux preparation require the external build tools listed above.
- Apple installation currently requires the Mac preparation and signing steps above.

Keep a separate backup of saves before installing a Preview or changing signing channels. For Android updates, stay with the same APK signing channel.

## What's next

Full PAK loader support, similar to ReMasked.

## Feedback

When [reporting an issue](https://github.com/OTPR26/Ocarina-ReTuned/issues), include your platform, device, Preview version, controller, graphics settings and steps to reproduce it. Mention whether a texture pack is enabled. Do not attach ROMs, prepared game modules, signing credentials or personal account information.

## Development

Python 3.11 or later is required for the Python tools and tests:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m retuned inspect-rom /path/to/game.3ds
PYTHONPATH=src python3 -m retuned inspect-textures /path/to/textures
```

[Source pins](resources/source-pins.json) and [native targets](resources/native-targets.json) record the project references and platform targets. ROMs, extracted game data, generated game modules, saves and signing material stay local and are excluded from distribution.

## Credits and licensing

- [TriAevum](https://github.com/coccofresco/TriAevum) — native runtime and translation foundation.
- [Ocarina ReFramed](https://github.com/OTPR26/OOT3DHud) — single-screen gameplay integration and HUD resources, including Project Restoration-derived work.
- [Majora ReMasked / DekUI](https://github.com/OTPR26/DekUI-Fork) — startup and settings reference.

ReTuned Dialogue is based on [Liberation Sans](https://github.com/liberationfonts/liberation-fonts) under the [SIL Open Font License](resources/fonts/LICENSE.txt).

Bundled components retain their original license and attribution notices. The Preview includes the approved ReFramed UI and Game Over resources alongside the ReTuned Dialogue fonts. Source-code licenses do not grant rights to game content.
