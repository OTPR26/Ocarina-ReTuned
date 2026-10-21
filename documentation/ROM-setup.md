# Local ROM preparation

First-run setup is under development. It is not a release-ready ROM importer yet.
The desktop pipeline has prepared a clean ROM, compiled its native module, and
rendered the opening scene in an isolated data directory. Android's bundled
compiler has compiled, linked and executed a local test library on the Odin;
the complete Android preparation flow is being tested on-device. The first-run
ROM picker, isolated foreground service and invalid-ROM retry have passed on
the Odin. Full native module linking and gameplay verification remain.

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
The production toolkit and complete gameplay handoff still require verification.
