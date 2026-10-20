# Ocarina ReTuned

A native Ocarina of Time 3D application prototype targeting Apple Silicon macOS
and ARM64 Android. The gameplay UI will use Ocarina Reframed's single-screen mod;
Majora ReMasked provides the reference for startup, settings and importing.

The native experiment uses TriAevum's runtime and ahead-of-time translation
infrastructure. A shared ARM64 architecture does not make macOS and Android
modules interchangeable: each requires its own ABI, renderer integration,
input, storage and lifecycle validation. The base Mac prototype reaches gameplay;
the Reframed integration is being tested separately.

## Current work

- Verify the Mac native module loader and input/audio/filesystem services.
- Cross-build the Android native services and Vulkan/NRI foundation.
- Build the neutral Mac runtime without game code or restricted graphics modules.
- Prepare and translate user-owned ROM content locally, outside published source
  and build artifacts, then connect the native title to the runtime.
- Validate native 30 Hz boot before adding the Reframed HUD and interpolation.

The `Native ARM64 prototype` workflow builds neutral runtime components on
GitHub. It receives no ROMs, extracted assets, generated title code, saves or
personal texture packs. Only neutral runtime bundles may be uploaded; generated title libraries stay local.

## Reframed integration

The native experiment applies the verified Reframed patch before title
translation. Its HUD, pause menus and camera run as translated mod functions,
with the original game save format. The host maps the injected code segment
instead of invoking the console loader's process-permission call. Native IRRST
shared memory supplies C-stick and shoulder input to the mod.

Game images, mod resources and translated title libraries are prepared locally
and are excluded from GitHub artifacts. Texture packs are referenced in place.
The active playtest is not switched until the new host and title checks pass.

## Development services

Python 3.11 or newer:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m retuned inspect-rom /path/to/game.3ds
PYTHONPATH=src python3 -m retuned inspect-textures /path/to/textures
```

The initial whole-ROM validator recognizes the published Reframed clean inputs.
Container-independent validation against the native runtime's executable,
ExHeader and RomFS identities is being integrated for equivalent dumps.
Recursive texture discovery skips symlinks and leaves the pack in place.

## Data and distribution

Ocarina data stays separate from Majora ReMasked. The macOS data directory is
`~/Library/Application Support/Ocarina ReTuned`. Preserve startup-to-game
controller mappings through one authoritative input configuration.

Users supply ROMs and optional texture packs. Game-derived code, generated
models, extracted assets, personal paths, diagnostics and saves must never be
uploaded. iMMERSE and DLSS modules are disabled. Donor source keeps its own
licenses and notices; a source-code license does not relicense game content.

`resources/source-pins.json` and `resources/native-targets.json` identify the
references and targets. Ignored `work/` contains local reference checkouts and
private test inputs, never package inputs. No release is approved or published.

The Reframed frontend uses a blue unified settings menu. Gameplay dialogue
retains the mod’s 80% layout. HD Latin coverage loads automatically from the
locally prepared font pack beside the process manifest, independently of donor
UI textures; no font-size or HD-font toggle is exposed. Fonts remain local user
data and are not bundled into the app.
