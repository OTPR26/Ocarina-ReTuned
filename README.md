# Ocarina ReTuned

A native Ocarina of Time 3D application prototype targeting Apple Silicon macOS
and ARM64 Android. The gameplay UI will use Ocarina Reframed's single-screen mod;
Majora ReMasked provides the reference for startup, settings and importing.

The native experiment uses TriAevum's runtime and ahead-of-time translation
infrastructure. A shared ARM64 architecture does not make macOS and Android
modules interchangeable: each requires its own ABI, renderer integration,
input, storage and lifecycle validation. There is no playable ReTuned build yet.

## Current work

- Verify the Mac native module loader and input/audio/filesystem services.
- Cross-build the Android native services and Vulkan/NRI foundation.
- Build the neutral Mac runtime without game code or restricted graphics modules.
- Prepare and translate user-owned ROM content locally, outside published source
  and build artifacts, then connect the native title to the runtime.
- Validate native 30 Hz boot before adding the Reframed HUD and interpolation.

The `Native ARM64 prototype` workflow builds neutral runtime components on
GitHub. It receives no ROMs, extracted assets, generated title code, saves or
personal texture packs, Only neutral runtime bundles may be uploaded; generated title libraries stay local.

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
