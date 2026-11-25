# Randomizer integration audit

Status: private Mac runtime proof and initial reward/save tests passed, 2026-11-24.
The audit below records the original design constraints; see the progress sections
for implemented work. Production activation remains disabled.

## Recommendation

Use OoT3D Randomizer's generator and gameplay logic, with SariaUI's portable-generator work as a reference. Integrate the gameplay changes into ReTuned's existing preparation and translated module. Do not import SariaUI's emulator, instruction interception, or prebuilt guest payload as a second runtime.

SariaUI is an Azahar-based implementation, not another native recompilation pipeline. Its implementation demonstrates integrated seed generation and file management, but does not establish compatibility with ReTuned.

Audited SariaUI revision: `40703bf55b05ab2dda0933a5c5007730b05cebe2`.
Its pinned OoT3D Randomizer revision: `d695cf5ad78dc1990da200af601b054860d707b8`.

## What ReTuned already provides

- `tools/native/rom_setup.py` verifies and normalizes inputs, installs resources, applies ReFramed, discovers code entries, translates the image, compiles it, and atomically activates an installation.
- `tools/reframed/prepare_native_image.py` incorporates ARM ELF symbols into translation coverage and publishes frontend capabilities in the process manifest.
- `tools/frontend/reframed_settings.h` invokes prepared game functions through the runtime bridge. This is an existing route for activation and configuration, rather than a new emulator interface.
- Preparation identity and source/object caches can distribute one randomizer-capable module update. Ordinary seed changes should not alter the generated executable or invalidate those caches.
- Existing resource, controller, touch, HUD, and platform abstractions remain the presentation layer.

These facilities reduce the infrastructure needed. They do not eliminate the work to combine game hooks or verify progression logic.

## Concrete incompatibilities

### Shared injection address

ReTuned's `prepare_native_image.py` uses `INJECTION = 0x5C7000`. SariaUI's `randomizer/data.h` and guest linker script start at the same address. Loading both payloads unchanged would overlap ReFramed.

Build a coordinated module with an explicit linker layout, symbol ownership, and bounded data arenas. Audit the current 0x600000 IPS-offset limit, process segment construction, executable coverage, BSS, and maximum mapped memory before increasing the mod size. Do not fix this merely by changing one address constant.

### Different execution model

SariaUI's `randomizer/hooks.h` substitutes ARM instructions, introduces custom SVC dispatch, tracks code epochs, and supplies invalidation ranges. Its guest build deliberately excludes loader, camera, graphics, save, and file-selection patches handled elsewhere by its host.

Those excluded responsibilities must be accounted for in ReTuned. Build a hook-ownership table: original instruction, randomizer replacement, ReFramed replacement, combined behavior, displaced-instruction handling, and return targets. Require a deliberate composition for every overlap; never resolve conflicts through patch order.

ReTuned must translate all randomizer functions, callbacks, assembly entry points, and adjusted returns before gameplay. Writing new ARM instructions to memory after translation cannot be assumed to update the compiled C++ behavior.

### Region and address assumptions

SariaUI's guest builder selects USA, and its integration checks fixed USA instruction signatures and save addresses. ReTuned normalizes supported USA/EUR inputs before applying its canonical mod image. Original input region is not the address space the hooks execute in.

Target ReTuned's canonical executable and validate original bytes at every patch site. Use upstream EUR address information only where verified against this image. Validate resource IDs, language-specific messages, and save semantics separately for USA and EUR. Do not claim Asian or Master Quest support from this integration alone.

### Platform dependencies

SariaUI's generator is a standalone C++20 executable with Qt Core resources and a portability layer; its service launches it as a subprocess. ReTuned should expose generation as a portable library with an optional desktop CLI. Keep Qt UI, QProcess, emulator memory objects, and multiplayer dependencies outside the core.

This avoids making desktop subprocess behavior a requirement for Android, iOS, tvOS, or Switch. Generation should use a bounded worker, report progress, and support cancellation without touching an active save. CPU, memory, determinism, and reentrancy still require measurement; upstream global state may require serializing generation.

## Proposed architecture

1. **Generator library:** pinned logic, canonical settings, explicit seed, deterministic RNG, progress, cancellation, and a versioned output schema. Start with a small supported settings subset; reject unsupported options.
2. **Compiled gameplay integration:** integrate item overrides and progression hooks into the prepared module. Preserve ordinary behavior when randomizer is inactive. Gate capabilities in the manifest so older modules never expose unusable controls.
3. **Seed data:** validated item/location tables, starting inventory, messages, rules, and required extended state. Use named fields with sizes and semantic checks, not arbitrary addresses or executable patch imports. Require schema, generator revision, logic revision, runtime capability, and content identity.
4. **Activation:** only at a safe pre-game/new-file boundary. Clear prior seed state, validate the full package, install data atomically, and initialize gameplay. Reject mismatched packages rather than silently loading an ordinary game.
5. **UI:** a Randomizer page in ReTuned's existing settings/startup flow. Settings affect a new run; existing runs retain their saved rules. Show seed identity and compatibility errors. Keep multiplayer out of the initial scope.

For any upstream option that changes executable instructions, compile both behaviors behind a validated setting or omit that option initially. Data-only seed changes are an architectural requirement to prove, not an existing capability.

## Saves are a release blocker

A randomized run needs native saves, seed identity, seed tables, and extended progression state. A seed string alone is insufficient, especially across generator versions.

ReTuned's current Apple sync explicitly permits seven ordinary files and validates fixed sizes. Android's documented transfer flow likewise handles ordinary save files. Neither should be assumed to preserve randomizer sidecars.

Introduce a versioned run bundle and a transaction/journal linking each native save generation to the corresponding extended state. Define interruption recovery before enabling writes. Export/import, Android custom folders and conflicts, Apple recovery/sync, portable-mode migration, slot copying/deletion, and update retention must all preserve this bundle. Ordinary Citra/Azahar save import remains supported as ordinary saves; do not interpret those files as complete randomized runs.

Use isolated randomizer profiles for the first playable test, protecting normal saves. A polished mixed-slot interface can follow once copying, recovery, and seed association are verified. Do not reuse SariaUI's reserved save-byte marker without confirming it against our supported save layouts.

## Compatibility with existing features

- Keep ReFramed responsible for HUD, pause menus, file-selection layout, save access, and controller/touch mapping.
- Audit randomizer effects on item acquisition, actor initialization, chest contents, shops, messages, inventory, scene transitions, death, and save initialization.
- Manual jump and other progression-changing options need an explicit policy. Initially validate seeds against ordinary glitchless logic; do not silently claim jump-aware logic.
- Cheats can invalidate intended progression. Preserve user choice while clearly distinguishing assisted runs from logic validation.
- Verify randomized rewards with original player models first, then PAK models and custom textures. Do not combine unrelated rendering changes into the first proof.
- iOS/tvOS still require the new runtime to be included in the prepared signed app once. Later data-only seeds should not require resigning, provided the generator and runtime are already bundled. Switch likewise needs an updated prepared runtime before seed-only switching can work.

## Implementation order and acceptance gates

1. Extract the host generator into a small portable build. Compare a pinned corpus of seeds/settings against upstream output; test identical results on x86-64 and ARM64. Preserve attribution and review individual file licensing before reuse.
2. Produce the hook-conflict and memory-layout audit against the current canonical image. Prove full translation coverage and ABI/calling-convention correctness for added code.
3. Implement one fixed Original-layout item-randomized seed in an isolated profile. Verify chest, NPC, shop, dungeon reward, starting inventory, repeat-check prevention, save/load, death/Continue, and ordinary-mode restoration. Complete a seed before claiming a playable randomizer release.
4. Add generation, validated seed import, UI, and save-bundle transactions. Prove changing seeds does not trigger preparation. Test cancellation, corrupt/missing sidecars, version mismatch, and interrupted saves.
5. Expand settings and platforms after the shared core passes. Entrance shuffle, Master Quest, multiplayer, and external seed-format compatibility are separate milestones.

## Reuse and provenance

SariaUI's integration files examined carry GPL-2.0-or-later notices; its vendored randomizer carries upstream license notices. Review the exact files and combined distribution obligations before incorporation. Do not assume that the upstream license covers all SariaUI modifications. Retain required notices and corresponding-source obligations where applicable.

Do not redistribute upstream guest binaries, reward assets, or resource archives merely because they are checked in. Establish provenance and rebuild approved code; derive any required game data locally from the user's verified ROM. This audit downloaded only selected source text for review and made no remote changes.

## References

- https://github.com/tgacquin/oot3d-sariaui/blob/40703bf55b05ab2dda0933a5c5007730b05cebe2/tools/oot3d/randomizer/CMakeLists.txt
- https://github.com/tgacquin/oot3d-sariaui/blob/40703bf55b05ab2dda0933a5c5007730b05cebe2/tools/oot3d/randomizer/build_guest.py
- https://github.com/tgacquin/oot3d-sariaui/blob/40703bf55b05ab2dda0933a5c5007730b05cebe2/src/oot3d/randomizer/hooks.h
- https://github.com/tgacquin/oot3d-sariaui/blob/40703bf55b05ab2dda0933a5c5007730b05cebe2/src/oot3d/randomizer/service.cpp
- https://github.com/gamestabled/OoT3D_Randomizer/tree/d695cf5ad78dc1990da200af601b054860d707b8


## Native integration progress (24 November 2026)

The private combined image now carries all thirteen preset runtime tables and
255 relocated custom messages. The host loads its native title plugin, completes
randomizer initialization, and reaches ReFramed file selection. Creating a new
file publishes paired native/extended state; a fresh process finds the file and
loads its matching extended state. The corrected build reaches Link’s house and
Kokiri Forest with the ReFramed HUD. An ordinary in-game Save completes, and a
fresh process reloads the matching state and returns to gameplay. The starting
Spirit Medallion matches the generated placement. Mido's Heart Container and
Saria's Fairy Ocarina were delivered and persisted across fresh-process reloads.
The user confirmed Mido's chest remained open. This is a fixed-preset smoke test,
not full-seed acceptance.

Live testing found three integration assumptions that unit-only checks missed:

- A bulk snapshot crossing native text/rodata/data regions failed. Only the
  object table is needed, so initialization now snapshots that mapped table.
- The payload queries Citra identification. The private native host answers that
  exact query as non-Citra; unrelated unsupported queries remain errors.
- New-file creation bypasses the normal save hook, and the normal hook can run
  after the filesystem write. New-file initialization marks state ready, while
  each native write captures current extended state at the paused guest boundary.

A compiler-generated byte-offset switch caused a dynamic dispatch miss after
loading the new save, despite complete static CFG coverage. The proof payload
now uses explicit branches (`-fno-jump-tables`); gameplay and reload pass with
that correction.
Ordinary game compilation and installed apps are unchanged.

The custom reward archive was fetched from the pinned revision for the private
runtime experiment only. The project owner subsequently approved including this community archive; source and credits are recorded in the Randomizer notices. A separate private
RomFS retains the existing UI resources, adds the reward archive, and verifies
all appended contents by reading them back. No game data was uploaded.


## Integrated new games and shared runtime (24 November 2026)

The private Mac launcher now uses a page inside the existing startup window,
with persistent draft seed and mode selection. New runs enter native name entry,
create paired native/extended state, and load gameplay. The earlier run's save
hashes remained unchanged.

A seed-independent image path and C++ activation adapter now separate executable
preparation from seed creation. Two generated seeds have identical code-image
hashes; activation reproduces their baked table/message bytes. The common launch
adapter binds seed data to an installed module without a compiler or subprocess.
The shared-runtime Mac test also passed integrated new-game creation and
fresh-process Continue into gameplay. Generation ran inside the app, reused
the module, and preserved all eleven earlier run files. Production activation
remains disabled pending platform launch/lifecycle wiring, save-transfer
integration, and the existing resource/progression gates.

## Run transfer and platform boundaries (24 November 2026)

The shared launcher now accepts and exports versioned run bundles. Each bundle
contains seed rules, runtime identity, and paired native/extended saves. Import
prepares and validates the matching runtime before reserving an empty slot;
occupied slots are never replaced. Menu callbacks reject transfers during
active gameplay or another operation. The desktop picker is connected in the private Mac test; mobile document
providers still need to connect to those callbacks.

Seven C++ test suites and sixteen patch/ABI tests pass. A round-trip of the
existing shared-runtime save also passes; hashes for all sixteen files across
the existing normal-save and randomizer-run folders remain unchanged. The
private receipt is `work/private/randomizer/transfer-smoke-receipt.json`.

The randomizer host patch now disables the ordinary Apple sync bridge for a
seed profile, preventing cloud download or tvOS ordinary-save recovery from
mixing native files with unrelated extended state. The bridge's disabled
configuration clears pending snapshots and invalidates in-flight work. Apply
this host patch after the standard platform save-sync patch. Apple syntax and
patch-idempotence checks pass; on-device randomizer cloud transfer is not
implemented. Randomizer tvOS recovery will need complete run bundles.

Production activation remains disabled. Remaining integration work:

- Desktop: register the validated runtime in production packages, verify Windows
  and Linux launches, and retain the app window during session changes. The
  private Mac test now uses the deferred native handoff without a Python supervisor.
- Android: connect document-provider byte streams and the existing separate-
  process restart helper, without changing ordinary save-folder synchronization.
- Apple: package the combined AOT runtime and implement a safe session handoff;
  keep run-bundle recovery separate from ordinary save recovery.
- Switch: adapt immutable save publication for filesystems without hard links.
- Wire retained runtime inventories into production packaging and updates. The
  shared resolver can select an exact matching retained module; if none matches,
  it preserves the run and refuses launch. This is not migration.
- Verify the pinned reward archive and keep the progression checks.

Bundles currently require the exact prepared code-image identity. Cross-platform
compatibility must be demonstrated before advertising cross-platform transfer;
matching filenames or a matching seed name are insufficient.

## Desktop import/export verification (24 November 2026)

The in-window run picker exported slot 1 and imported it into empty slot 2.
Continue launched the imported profile in a fresh process and reached Link’s
house; keyboard input opened Items and returned to gameplay. All sixteen
previously recorded normal-save and original-run files retained their hashes.
The exported document contains seed and save data, not the game module.

Replacing the macOS process in place rendered the game but left keyboard input
unresponsive in the test. Spawning a new process after guest/renderer teardown
resolved that observed failure. This is an interim handoff: the window still
closes and reopens. A persistent window and loading transition are not yet
implemented, and production activation remains disabled.

The export picker now reserves space for its filename and action buttons, fixing
a clipped footer found during the live test. Launch tests reject duplicate or
missing save-path arguments and mismatched seed/profile identities.

## Persistent-window prerequisites (24 November 2026)

The Continue/name-entry helper now belongs to NativeWidescreenProjectionState,
which is owned by the game session, rather than a function-local static. A new
session therefore cannot inherit the previous run’s completed Continue state.
Normal sessions keep the helper disabled. The private Mac build passes, as do
seven C++ suites and seventeen Python tests, including repeated patch application
and sequential randomized/ordinary Continue-state checks. This build has not
replaced the running test app.

The persistent-window transition still requires these changes:

- Separate SDL window ownership from renderer teardown. Currently
  GfxWindowBackendSDL2::Destroy destroys the window and calls SDL_Quit.
- Give title-module loading an explicit session lifecycle. ConfigureTitlePlugin
  rejects selection after the first query, and module/program pointers are
  cached in function-local statics. Guest callbacks must finish before changing
  those pointers or unloading a module.
- Reset frontend launcher bindings, active-slot state, input capture, and
  renderer resources when changing sessions; retain settings and run data.
- Verify normal → randomized → another randomized run → normal transitions,
  including failed launches and cancellation, in one process and window.

The existing fresh-process handoff remains active until those checks pass.

## Retained runtime resolution (24 November 2026)

Continue no longer assumes every existing run uses the newest installed module.
The shared launcher accepts platform-supplied retained module paths and validates
each candidate against the selected run before returning a launch request. The
private desktop host exposes that inventory through its local configuration.
Tests cover an incompatible current module with a valid retained module, no
matching module, wrong seed/runtime identity, and the production activation gate.
All seven C++ suites and the private Mac integration build pass. No live app was
restarted, no run was migrated, and no release gate was enabled. Production
updaters still need to preserve and enumerate the complete runtime files.

The owner has deferred persistent-window work. The verified fresh-process
transition remains the intended integration path for now.

## Local runtime staging (24 November 2026)

Added an opt-in `runtime_store` preparation step. Module, seed, layout, and
source digests are checked; referenced source files are retained by content
hash; manifest paths become relative to the retained store. Publication uses
a staging directory, and repeated staging verifies/reuses existing files.
Production use rejects unapproved proof runtimes. Tests verify retained files
after removing the fixture build directory and ensure repeated staging does
not change existing files. All eighteen Python checks pass.

No real ROM/resources were copied or deleted, no app was restarted, and no
release package was changed. Production updater inventory wiring and a live
retained-runtime migration remain outstanding.

## Retained inventory integration (24 November 2026)

NativeLauncher now accepts a runtime-store directory and discovers completed
runtimes there when its original launch manifest/module cannot be used. It
validates the run’s stored seed and exact code identity, then builds a separate
per-seed launch manifest from the matching retained template. It does not
rewrite old manifests or saves. The private desktop host passes `runtime_store`
through to this shared adapter.

The real prepared runtime was staged into the private store (approximately
569 MB), and the existing slot-1 run passed restoration, seed/runtime validation,
and source-path checks against that store. This exposed and fixed missing
relocation of exheader_path: all source-path dependencies now relocate together.
Missing inventories, wrong runtime identities, and the production gate were
also checked. All seven C++ suites pass. The sixteen recorded original save/run
files remained unchanged. Receipt: work/private/randomizer/runtime-retention-receipt.json.

This verifies preparation and resolution, not a new gameplay launch. The
running app has not been replaced. Android/Apple/Switch adapters and release
packaging remain incomplete; production activation is still disabled.

## Retained gameplay and Android document bridge (24 November 2026)

The private Mac launcher resumed gameplay using the retained runtime, including
Continue from imported slot 2. Startup mode arrows are restored. All eleven
files in retained-launch-before.json remain unchanged; the private receipt is
seed-independent/retained-gameplay-check.json. The observed yellow file-selection
corners were selection brackets; a separate transient artifact has not been
ruled out.

Android NativeLauncher now owns a document-transfer adapter. The activity opens
the system document picker and exchanges bounded bytes with the native importer;
URI access stays in Java. Imports are rechecked against startup state and an
empty destination slot before validation by the existing run importer. Pending
transfers disable run actions. Cancellation, repeated activity results, and
provider errors do not write saves. Imported bytes retain their exact UTF-8
representation across JNI.

Validation: eight shared C++ suites, eighteen randomizer Python checks, two
Android document checks, Java compilation against Android API 35, and ARM64 NDK
syntax compilation of NativeLauncher with the JNI adapter. Tests cover occupied
slots, mismatched results, duplicate completions, cancellation, provider failures,
and the 10 MB limit. No device install or Android gameplay test was performed.
Production Android host registration, combined-game preparation, and restart
wiring remain prerequisites; the randomizer release gate stays disabled.

## Thor startup and transition review (24 November 2026)

The private Android build now generates seeds on the Thor and reaches gameplay
with seed-specific save files. It uses a desktop-prepared combined module;
automatic combined-ROM preparation on Android remains unfinished. Normal saves
and launch arguments were preserved during installation.

The first install missed its randomizer data directory, leaving startup without
mode arrows. The launcher now validates and creates that directory. The user
reported misplaced selection brackets after naming, inconsistent D-pad placement,
weak startup focus feedback, and an unacceptable activity close/reopen transition.

The next private test retains the Android activity and renderer, drains the old
guest, resets title/renderer state, and starts a separate guest with the selected
save profile. Module handles remain retained; active guest execution prevents a
module reset. This path still requires device validation before production use.
The native file flow now completes the occupied-slot transition before requesting
Start, rather than drawing the Start cursor over the file list. Startup rows use
the same focus treatment. A private compatibility adapter moves only the D-pad
of the retained proof HUD; current images with group-size exports bypass it.
The Thor's overall HUD setting remains 100% as requested.

### Thor follow-up checks

The retained-session test continued slot 2 into gameplay with the same Android PID. All 20 checked normal/randomizer save and configuration files matched across installation. The user accepted the translated D-pad at the unchanged 100% HUD setting. Startup rows are right-aligned, use a left-fading highlight without the navigation outline, and accept left-stick mode changes as well as D-pad input. The post-naming yellow-bracket transition still requires a new-file visual check.

The shoulder shading test maps the existing circular-button artwork onto the shoulder outline; generated-mesh bounds and UV seams pass. The private retained-image adapter is gated to the legacy randomizer HUD and its exact buffer addresses. Its runtime appearance remains under review.

### HUD artwork review follow-up

The user confirmed vertical and horizontal left-stick navigation. The first radial shoulder texture mapping was rejected for curved reflections; the next version separated a 32-segment rim from a 32-segment glass interior. The user found the rim too thin, the replacement action base vertically inverted, and its label obscured. The pending test uses a wider rim, explicitly top-first action-face UVs, and preserves the native action text coordinates in a later overlay layer. Visual acceptance is still pending.

A prior-run guest memcpy fault at 0x00371750 was retained in `work/private/randomizer/android/before-revised-native-stderr.log` and the companion summary before dismissing the diagnostics screen. Its cause has not yet been established; the following launch reached startup and gameplay.

### Shared HUD compatibility check (November 24)

The retained Android randomizer image predates independent HUD-group sizing.
Its gameplay D-pad now uses the current native base coordinates, Restoration
scaling, icon enlargement, and left anchor; normal games retain their existing
native layout. The fallback reads the saved HUD and D-pad percentages, and is
idempotent across repeated uploads. Both presets and all supported scale pairs
pass the local geometry test. Normal and randomizer gameplay captures at 100%
match the user's approved normal-save reference.

The shoulder geometry/UV and clean-action rendering no longer require a
randomizer manifest. The action overlay is gated by the gameplay context and
pause state; this removes the unused "Faster" label exposed on the title demo.
Device logs confirmed both shoulder geometry and UV uploads. The rim was then
widened without changing the outer shape to avoid compressing the native bevel
into a thin outline. Final visual approval of this border is pending.

Each private update preserved hashes of the 20 checked save/config files.
No ROM preparation, save conversion, remote publication, or workflow run was
needed for these host-side compatibility changes. Independent group controls
remain unavailable in the retained image's settings UI until its missing native
exports are implemented; saved D-pad size is honored by the fallback.

### Naming approval and Android compiler handoff (November 24)

The user accepted the rounded shoulder artwork and confirmed the temporary
Slot 3 naming transition was fine. The temporary run was removed afterward;
all 17 existing normal-save and Slot 1/2 files matched their baseline hashes.
The opposite shoulder is generated as an exact horizontal mirror.

Randomizer preparation now accepts the existing Android preparation backend
for its compilation stage, retaining SDK integrity checks, bounded workers,
object/module caches, cancellation, and ABI verification. The desktop CMake
path is unchanged. All 24 randomizer Python tests pass, including rejecting
SDK-integrity failures and invalid modules before returning a compiled result.
This is the compiler handoff only: composition/translation still invoke desktop
Python subprocesses, and Android service registration and an entirely on-device
combined-image preparation test remain unfinished. Production activation stays
disabled.

The Android preparation adapter now runs image composition, translation, and
source generation through embedded Python. It keeps device-built modules separate
from desktop builds and keys their reuse to the toolkit and the verified input
manifests. The Android launcher does not yet invoke the adapter. The native
compiler and runtime handoff still need a full Thor test.

### Android launcher handoff (November 24)

An opt-in Android launcher now sends new-run preparation to the existing
isolated service. A private request carries the generated seed. The service
reports progress and cancellation separately from normal ROM preparation and
retains each verified runtime before the launcher can create a slot. Existing
runs still resolve through the retained store.

The private preparation kit can stage the randomizer scripts and translation
support. A device test needs a local `device-preparation.json` with the matching
prepared image, runtime ELF and receipt, and resource manifest. The current
proof image was built against a different HUD ELF from the Thor kit. The
production activation gate remains disabled while the matching inputs and
on-device compile, boot, and save/reload checks are outstanding.

### Thor device preparation and Apple module builds (November 24)

The Thor compiled and linked all 67 units for one new seed, then booted it
into Kokiri Forest. All 20 checked existing save and settings files matched.
This was a private fixture test with a HUD matching the prepared image.
The app's preparation flow stays as tested.

Mac preparation now supports separate arm64 Randomizer targets for iOS
and tvOS using the normal Apple SDK settings. Both targets compiled from
the existing seed-independent generated sources. The Mach-O platform and
both public title ABI exports passed checks for each target.

The Apple host still needs to bundle and select the second framework.
Record the module checksum after signing that framework, since framework
signing changes the binary. IPA signing and on-device launch are pending.

### Private iPhone launcher (November 24)

Built and installed a separate, locally signed arm64 IPA with the shared
Randomizer framework, a private bootstrap seed, and the in-app generator.
The framework checksum is taken after framework signing and sealed in the
outer app. The bootstrap profile and the per-seed slots use the test app's
container. The regular iPhone app is still installed with its original
identifier. On the physical iPhone, Slot 1 generated a seed distinct from
the bootstrap seed, loaded it through the native session handoff, and wrote
a matching native and extended save pair. The owner confirmed gameplay passed.
The receipt is in `work/private/randomizer/iphone/device-receipt/verification.json`.

The iPhone comparison used the regular app's live touch-on and touch-hidden
screens as references. The regular app has a saved custom bottom-row Map
position and X Jump. The isolated test now has the same touch and HUD
preferences, a bottom-row default Map button, the floating movement stick,
and Android's HUD geometry and artwork adapters.

iOS app updates relocate the bundle. The launcher now rebinds an existing
seed to the current bundled framework after verifying the runtime identity.
Slot 1's seed and paired save survived the update. On-device logs confirmed
Continue, extended state load, and movement input. The owner confirmed
the updated iOS test passed.

### Combined iPhone test and platform scope

The combined, privately signed iPhone app opened normal file selection through
Start Game. Randomizer → Slot 1 → Continue resumed the existing Kokiri Forest
save after the update. The pre-update and post-update seed, native save,
extended state, and configuration files matched.

Windows and Linux receive the shared startup and HUD cosmetic changes in this
release. Their launchers keep normal file selection and omit the Randomizer slot
selector and settings category. Gameplay checks for those platforms are deferred.

Randomizer targets are Mac, Android, iOS, tvOS, and experimental Switch. The
Apple TV launcher has a compile check only. In Ryujinx, the Switch launcher selected the statically linked randomized title,
created a named file in Slot 1, and resumed it in Link’s house after a cold restart.
Physical Switch testing is outstanding. Public packages must be reproducible
without the private test ROM, seed, or signing profile. Preparation uses the pinned community reward archive.
