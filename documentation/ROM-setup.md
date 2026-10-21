# Local ROM preparation

First-run setup is under development. It is not a release-ready ROM importer yet.
The desktop pipeline has prepared a clean ROM, compiled its native module, and
rendered the opening scene in an isolated data directory. Android's complete
first-run flow has passed on an ARM64 device: the document picker, sealed tools,
isolated foreground service, translation, native compilation/linking, module
verification, atomic activation and handoff into the rendered opening scene.
Invalid-ROM retry has also passed. These tests used separate app identities and
preserved the existing game installation and saves.

The Preview requires Android users to be able to choose and prepare their ROM
on the device. A desktop companion is not a substitute for that requirement.
iOS and tvOS require their locally generated module to be included before signing.

## Inputs and output

The currently verified input is a clean, decrypted USA Ocarina of Time 3D
cartridge dump (`.3ds` or `.cci`, program ID `0004000000033500`). Setup checks
extracted file sizes and SHA-256 identities before translation. It includes no
keys or decryption service and uploads no ROM data.

`tools/native/rom_setup.py` coordinates extraction, COPY-only executable
normalization, resource-region normalization, our HUD patch, complete native
translation, local C++ compilation, module ABI verification, and activation.
`tools/native/android/rom_preparation.py` runs the same preparation stages with
embedded Python and APK-installed compiler/linker executables. It does not need
Git, CMake, Termux, or a desktop computer on the user's Android device.

Generated game files are private local output. Never add them, test ROMs,
compiled title modules, audit fixtures, or private preparation kits to the
repository or public build artifacts. A distributable preparation kit needs
its own source/dependency notices, integrity checks, privacy audit, and complete
first-run tests before publication.

## Preparation source bundle

`tools/native/stage_preparation_sources.py` reconstructs an explicit allowlist
from pinned upstream Git objects and applies the same generic ARM/runtime fixes
used by the host. It retains structural entry boundaries while removing unused
annotation, instruction-summary and string columns. Its manifest records original
and staged hashes, patch identities and the upstream source revision. Bundled
trees pass integrity checks without shipping Git history. The explicit-input
source generator does not read upstream developer operational-input settings.
Compiler SDK notices and platform package audits remain separate release gates.

## Desktop build tools

The staged desktop toolkits include a platform-specific Python runtime,
Capstone and neutral JSON headers. The portable Windows candidate additionally
bundles pinned LLVM-MinGW, CMake and Ninja. Its compiler is used for both the
host and the game module because their C++ memory interfaces must match.
Preparation uses only the bundled tools and Windows system executables, ignoring
installed Visual Studio environments. Users select a ROM and wait in the setup
screen; no developer-tool installation or Developer Command Prompt is intended.

The portable Windows candidate is being validated and is not a release asset.
Older Windows test kits still discover installed Visual Studio Build Tools.
Linux currently requires CMake 3.30+, Ninja and a C++20 compiler with system
headers. Real Windows bundled-tool preparation and gameplay have passed, including
controller input and persistent HUD/dialogue with the matching private UI pack.
Linux gameplay, complete toolchain notices/provenance, and final package audits
remain release gates. Wine compiler
checks alone do not establish real Windows gameplay compatibility.

## Installation transaction

Preparation runs in a temporary directory under the selected app data root.
A lock rejects concurrent setup writers. Failed or cancelled setup removes its
partial data and leaves the existing launch profile intact. Activation first
publishes an immutable installation directory, then atomically switches the
launch profile. Existing profile arguments are preserved apart from the module
and process-manifest paths. Save files, controller mappings and preferences
are outside the installation directory and are not replaced.

The desktop bootstrap runs before loading a game module. It supports a file
chooser, typed paths, drag-and-drop, progress and cancellation. Diagnostic CLI
commands bypass the setup window. Android uses a native first-run ROM picker
and an isolated foreground preparation service, with progress, cancellation and
interruption recovery. Generated native modules remain in internal app storage;
the existing external app directory retains saves, preferences and launch settings.
The original launcher component is preserved for existing home-screen shortcuts.
Android's sealed toolkit and opening-scene handoff have passed. Final public
package provenance/notices and desktop platform checks remain release gates.

## Bundled UI resources

The preparation package includes `native-ui.zip`; setup does not download UI
resources. `stage_ui_resources.py` builds it locally from the explicitly supplied,
pinned Reframed release archive, selecting six matching UI files and preserving
five original notices. `native_ui_resources.json` records the source and exact
resource hashes. Runtime preparation verifies the complete pack before applying
it to a new copy of the normalized ROM. It preserves the user's original ROM.

Kits may explicitly specify `ui_resources` and an optional `hd_font_coverage`
path. The latter must match the bundled native font and is copied beside the
installation manifest, where the renderer discovers it. The tested Single Screen Experience private
64-pixel coverage pack remains local pending redistribution authorization;
including a resource in a local test does not establish public distribution
rights. Source repositories contain integrity metadata and packaging code, not
these resource bytes. Final public-resource rights and package audits remain
release gates.

## ReTuned Dialogue fonts

The app bundles Regular and Bold versions of ReTuned Dialogue under the SIL Open
Font License. They derive from the unchanged Liberation Sans source faces, with
an original diamond marker and adjusted bitmap spacing. The modified fonts use
the ReTuned Dialogue name; their copyright and OFL notice remain in
`resources/fonts/LICENSE.txt`. `ReTunedDialogue-Styles.json` pins both native and
128-pixel HD assets by SHA-256.

Settings → HUD → Dialogue font saves the choice locally on that device. Bold is
the default. Restart the app after changing it so the cached native text and its
HD coverage use the same face. Save states may retain previously drawn text until
it is redrawn; subsequent native lookups select the configured face before its
metrics are read. Fonts are not part of iCloud save sync. Arbitrary user font
installation is not exposed.

`tools/native/prepare_open_font.py` rasterizes the approved faces at build time.
The fonts retain their natural shapes, share a baseline, and include extra
trailing clearance after lowercase t. Layout measurements are independent of
atlas density. The runtime uses smooth sampling only for validated HD font
coverage; unrelated texture samplers remain native.

Local ROM preparation uses only the Python standard library to create a choice
pack with both faces and the exact source-font identity. Before native character
lookup, the host replaces only a byte-matching recognized font in guest memory,
and only after checking matching character/cell geometry and allocation bounds.
It does not rewrite the user's ROM. The resulting `font_coverage.zip` includes
native game data for that identity check and stays private to the installation.
The public font assets contain only OFL-derived glyphs and the original diamond,
without native game artwork or the separately authored Single Screen Experience
HD font. Pillow is needed only by the package builder; users do not download a
font or install a rasterizer.
