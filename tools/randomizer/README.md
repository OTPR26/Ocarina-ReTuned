# Randomizer development proof

The Qt-free generator builds and produces a deterministic fixed-preset seed.
The combined runtime boots in an isolated Mac proof runner. **Gameplay and
save/reload have passed the initial chest and NPC checks**; the output cannot be imported
into a normal installation.

Fetch only pinned source (no ROMs, payload binaries, or texture resources):

```sh
python3 tools/randomizer/fetch_source.py work/private/randomizer/source
cmake -S tools/randomizer -B work/private/randomizer/build -G Ninja \
  -DRANDOMIZER_SOURCE="$PWD/work/private/randomizer/source" \
  -DCMAKE_BUILD_TYPE=Release
cmake --build work/private/randomizer/build --parallel 4
ctest --test-dir work/private/randomizer/build --output-on-failure
work/private/randomizer/build/retuned-seed retuned-proof-001 work/private/randomizer/seed-001
```

Requires C++20, CMake, and nlohmann/json headers. `JSON_INCLUDE_DIR` can point to
existing preparation-kit headers. The generator does not need Qt, a ROM, a game
installation, or an emulator. The CLI refuses an existing output directory and
publishes seed.json only after successful generation and serialization.

The library serializes calls because the pinned logic uses global mutable state.
Progress callbacks occur at the start of each fill attempt; throwing cancels the
attempt. This is not yet fine-grained cancellation during an attempt. Initialization
runs once; default settings reset before each generation. Tests exercise A/B/A
seed generation and cancellation followed by another deterministic generation.

The initial preset is Original-layout, child-start, glitchless, normal entrances,
normal songs, and normal shop stock, with keys kept in their own dungeons.
Dungeon rewards and the supported item pool are randomized. The generator's
beatable-placement result is a logic check, not a completed in-game playthrough.

The schema is explicitly a development proof. It includes item placements,
settings bytes, relative message data, dungeon rewards, and spoilers. It includes all thirteen runtime tables for this preset and sets
`runtime_ready: false` until integration testing passes; nothing
should reinterpret it as an existing SariaUI seed format. The native adapter
must still supply and validate the matching ABI, reward assets, extended saves,
and native save ordering.

## Runtime audit

`fetch_source.py --runtime` fetches the matching runtime source into a separate
new directory. `build_runtime_probe.py` builds an EUR-addressed ARM ELF at
0x680000, away from ReFramed, using an explicitly supplied ARM compiler.
It does not install, patch, or activate a game. `audit_runtime.py` compares its
patch sections with a supplied HUD ELF. Patch sections are included even when
the ELF does not mark them allocatable.

`hook_policy.json` records which overlapping behavior remains owned by ReFramed
and which hooks require composition. It is a review plan, not an override switch:
`plan_hooks.py` rejects unknown, missing, or ambiguous overlaps. `compose_image.py` consumes this plan, validates exact ELF and seed hashes,
and creates a private combined image. Production activation remains disabled.
The current probe has 478 patch sections, with eight overlap ranges against the
installed Mac setup HUD ELF. Relocating the payload alone is insufficient.

The next integration stage must use a newly created isolated profile with new
save files. It must not overwrite or migrate the user's existing save directory.
See ../../documentation/randomizer-integration-audit.md and NOTICE.md.

## Composed-hook and seed checks

Passing `--hud PATH` to `build_runtime_probe.py` composes both update hooks with
that exact ReFramed binary. Its receipt binds both ELF hashes. `plan_hooks.py`
checks that receipt and assigns all eight conflicts; loader, camera, movement,
and Select remain owned by ReFramed. The generated ELF remains audit-only.

`validate_seed.py --seed SEED_JSON --runtime RUNTIME_ELF --output RECEIPT`
checks all thirteen seed tables against guest symbol sizes and checks relocation
of relative custom-message entries, including entrance, enemy, and audio data.

Run the rejection tests with:

```sh
python3 -m unittest discover -s tools/randomizer -p 'test_*.py'
```

## Isolated native services

`runtime_services.cpp` implements the six guest host-service calls: initialization
boundaries, extended-save load/initialization, unchanged prices for the fixed preset,
and explicit offline multiplayer status. Changed object archive names clear
cached archive sizes. This runner must not switch to ordinary gameplay in the
same process.

`save_store.cpp` binds each profile to the seed hash, exact runtime hash, and
extended-save ABI. A commit first publishes an immutable, checksummed record
containing both native and extended bytes, then atomically replaces the native
save. Failed/interrupted native writes leave old records intact. Missing,
corrupt, or mismatched state is rejected. Identical native bytes paired with
different extended state are rejected as ambiguous; no silent reset occurs.
Only one process may own a profile. Save-state restore and profile switching
are not supported by this proof.

`apply_host_services.py ENGINE` adds opt-in callbacks to a private engine tree;
it is deliberately not part of normal platform preparation. `host_adapter.h`
binds those callbacks to the isolated store and guest memory, routes its saves
to the profile's `native` directory, and intercepts full native slot writes.
The adapter requires the filesystem-backed host, not an alternate filesystem
backend. Normal builds have no callbacks installed.

Build the service tests with an existing engine, without rebuilding the app:

```sh
cmake -S tools/randomizer -B work/private/randomizer/build \
  -DRANDOMIZER_ENGINE="$PWD/work/private/mac-current/engine"
cmake --build work/private/randomizer/build --parallel 4
ctest --test-dir work/private/randomizer/build --output-on-failure
```

The service tests cover seed identity, restart/reload, interrupted commits,
corruption, write-boundary capture, copies, and object-cache invalidation. macOS persistence
has been exercised; Windows/Linux persistence has not. Guest memory and host
bindings compile against the cached engine, and are wired into the isolated combined-image runner. New-file creation, an ordinary in-game save, and fresh-process reload into gameplay
have passed in the guest. The starting reward matches the seed. Mido's Heart
Container and Saria's Fairy Ocarina persist after fresh-process reloads; the user
also confirmed the chest remains open. Guest copy/erase flows remain under test; this is a private fixed-preset
proof, not a release candidate.

## Combined-image proof

`compose_image.py` retains ReFramed's loader, HUD, camera, movement, and Select
handling while composing both update hooks. The native frontend owns rendering
and sleep/title behavior. ARM undefined-instruction traps remain explicit faults.
`apply_translation.py` adds the CPSR flag restore and binary64 negated arithmetic
instructions needed by the new payload, only in the supplied private engine.

`apply_proof_runner.py` binds a seed-specific profile before constructing the
native host. It disables savestates and never reads ordinary gameplay saves.
The host answers only the randomizer’s Citra-identification query as a native
(non-Citra) environment; other unsupported system queries still fault.
The initialization snapshot covers the object table within one mapped data
region, rather than spanning separate native text/rodata/data mappings.
New-file initialization explicitly marks extended state ready because that path
bypasses the normal SaveGame hook. Every native write captures current extended
bytes while the guest is paused, so post-write hook notifications cannot leave
a stale snapshot for the next save.

`prepare_resources.py` creates a separate RomFS and round-trip checks its added
reward archive and existing UI resources. Preparation defaults to the pinned community artwork in `assets/` and verifies its
SHA-256 digest. Artist credits and upstream sources are in [NOTICE.md](NOTICE.md). No ROM,
combined image, generated title module, or save belongs in a release or source
commit. The native launcher must run with its bundle environment configured;
the development executable is not an installed app update.

The proof payload disables compiler jump tables: GCC byte-offset switch tables
need extra dynamic dispatch targets beyond the current static CFG analysis.
This does not change the ordinary game compiler settings.

For reward playtests, `inspect_save.py PROFILE --slot 0` validates the paired
record and reports native inventory, chest flags, health, magic, and both hashes
without changing the profile. Compare output before collection and after saving
and restarting; a table match alone does not prove in-game delivery.

## Startup and run management

`run_catalog` stores exactly three menu slots under `randomizer-runs` in the app's
data directory. Each has immutable seed rules, a seed hash, an exact prepared
runtime identity, and a separate `SaveStore` profile. Guest slot zero belongs to
that run; it is not the menu slot index. Ordinary saves are never used as a fallback.
Interrupted creation reserves an unavailable slot and preserves its files.
Creation never replaces an occupied slot. Seed integrity and runtime identity
are checked again when selecting a run. This is an internal catalog, not a seed
import validator; the preparation adapter must still validate the seed ABI and
bind the prepared runtime to that seed before calling it.

The shared frontend adds a Start game/Randomizer selector, an integrated three-slot page,
and a Randomizer settings category. These are gated on host callbacks, which are
not yet registered in production. Draft seed settings do not mutate current-run
rules. Creating/starting a run is disabled during gameplay or a busy operation.
Only the fixed tested Original/glitchless rules are presented.

`run_launcher` runs generation/preparation callbacks on a worker and returns a
launch request on the frontend thread. Before reserving a slot, it verifies the
seed digest, actual combined-image digest, extended-save ABI, and compiled-module
receipt. Continue repeats those checks against the stored run. Cancellation and
preparation failures leave occupied slots and ordinary saves untouched. A request
always targets guest file zero inside the selected run's isolated profile.

The preparation callback must produce the compiled module and a sibling
`<module>.randomizer.json` receipt with format `retuned-randomizer-module-v1`,
`code_sha256`, `seed_sha256`, and `module_sha256`, after building that exact image.
This is a trusted local build receipt, not authentication of imported modules.
The resolver must return the retained prepared artifacts for the selected slot.

`menu_binding.h` connects the frontend callbacks to this worker. Its host must
poll on the frontend thread and queue a fresh-process launch when ready. It
rejects launch requests during gameplay and prevents duplicate handoffs. Disk
validation runs on refresh/completion, not every rendered frame. The launcher
and menu binding are host-owned; destroy the binding before its launcher/menu.

The opt-in private Mac host now registers these callbacks through
`apply_private_launcher.py` and `private_launcher.h`. `prepare_run.py` composes
and compiles a seed-specific image, retaining verified artifacts for Continue.
`run_private_launcher.py` supervises fresh-process handoffs and rejects requests
outside the configured artifact/profile roots. Its logs have unique session names.
A newly generated seed has reached gameplay through the slot picker and saved
successfully. Continue has also restarted into the same seed and loaded gameplay; native and
extended save hashes were unchanged. The startup selector has been visually
checked with chevrons flanking its label, keyboard cycling, and confirmation.

Continue now selects guest file zero through the native load transition once
the slot list is ready. It validates the native save and code signatures before
requesting the transition, and does so only once per launch. The private Mac
test reached gameplay without file-selection input; both save hashes stayed
unchanged. This adapter currently targets the canonical EUR combined image.

The integrated page now enters native name creation directly for a new run,
then loads that file once creation completes. Continue loads guest file zero.
Draft seed settings and the last selected mode persist in the app configuration.
The private Mac creation test reached gameplay and published paired saves without
changing the existing run. No separate randomizer popup is used.

## Shared runtime integration

`compose_image.py --seed-independent` emits a fixed executable image and a bounded
seed layout. `seed_activation` validates all tables before applying them to a
freshly mounted guest, before guest execution. Message pointers are relocated
using the actual (not necessarily aligned) arena address. Unknown patches,
overlapping destinations, malformed tables, and out-of-range messages fail launch.
Two different generated seeds produce identical images, and the activated data
matches the original baked-seed images; only the intentionally relocated UDF
trap differs.

`BindSeedToRuntime` is the compiler-free C++ preparation adapter for platform
hosts. It validates the installed image/module receipt, writes an immutable
seed/manifest pair, and retains the shared module. `run_launcher` accepts the v2
module receipt only when the layout, image, module, and seed digests match.
The private preparation script supports `seed_independent: true` for building
that module once and reusing it for later seeds. Existing baked runs remain
supported and are not migrated or overwritten.

`native_launcher.h` connects this adapter and the in-process generator to the
same menu binding used by the tested startup page. Platform hosts can link
`retuned_randomizer_frontend` and provide their safe guest-restart callback;
no desktop-only UI or subprocess API is part of that class. The Mac test host
can opt into it through an `installed_runtime` manifest/module configuration.

The shared-runtime Mac test now creates a run through the integrated page,
publishes paired saves, and reloads gameplay through Continue after restart.
Generation runs in-process and uses the same compiled module as other seeds.
All eleven files belonging to the earlier test runs remained unchanged.

Remaining work: production platform adapters and the release gates below.
Production activation is still gated; do not enable the frontend merely because
generator callbacks exist. Normal-mode
return, cross-platform save transfer, and broader progression tests remain gates.

## Runtime retention across updates

`NativeLauncher` accepts an optional inventory of retained module paths after
the development flag. The platform supplies these paths from its own installed
runtime inventory, never from imported run documents. Continue checks the
current module first, then retained modules against the saved run’s manifest,
code identity, seed, module digest, and activation gate. A missing or incompatible
current module does not prevent a valid retained runtime from being selected.
If none matches, the launcher reports the missing runtime and leaves the run
intact. This is exact-runtime selection, not save migration.

Updaters must retain the module, its `.randomizer.json` receipt, referenced code
and resources, and per-seed manifests while runs depend on them. The resolver
does not copy or delete these files. Production package inventories and cleanup
policies still need wiring. The private desktop host accepts `retained_modules`
in its local configuration for testing this path.

`stage_runtime.py` provides the local retention step. It verifies the prepared
module receipt, code, layout, and seed; copies source-file dependencies into a
content-addressed store; and rewrites source paths relative to the retained
manifest. Repeated staging reuses verified source blobs and the same runtime
directory. Runtime directories publish only after their files are checked.
Preparation can opt in using `runtime_store`; proof builds additionally require
`allow_development_runtime: true`. Production activation remains gated.

This store contains user-derived private game files. It belongs in local app
data, never in release downloads. There is deliberately no automatic pruning.
Package/updater integration must retain it and enumerate its modules for
NativeLauncher. The current test host still uses its existing paths until the
real-data migration is explicitly exercised.

The optional `runtimeStore` argument to NativeLauncher enables discovery under
`runtimes/<content hash>`. When the original binding is unavailable, the launcher
validates a retained template and the run’s seed, then creates an independent
binding under `artifacts/retained`. All source paths, including the executable
header, are resolved against the retained template. The private host forwards
its `runtime_store` setting to this adapter.

## Android run documents

On Android, `NativeLauncher` owns `AndroidDocuments` and polls it on the frontend
thread. `prepare_android_app.py` installs its activity methods and system picker.
The picker exchanges bytes with the existing run importer; it never chooses a
runtime module or writes a normal save. Pending transfers block run actions,
and import completion checks startup state and destination availability again.
The Java and JNI code compile locally, but production Android startup/restart
registration and on-device tests are still required before enabling it.
