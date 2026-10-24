# Experimental Switch deko3d backend

This is an opt-in renderer integration for an isolated Switch engine build.
It is not a release backend. Unsupported rendering operations fail explicitly;
full texture-copy, mip/sampler, readback, and scene compatibility remain under
validation. Do not replace an existing working installation with this build.

The backend owns deko3d presentation, native PICA targets and draw state, ImGui
rendering, runtime GLSL-to-DKSH compilation, and a versioned persistent cache.
The Switch SDL driver retains input handling but allows an external display
without creating an EGL surface. SDL's OpenGL renderer is not selected.

## Local build inputs

- The project's privately staged, patched engine and user-prepared title archive.
- Official devkitPro Switch SDK and deko3d.
- devkitPro SDL `switch-sdl-2.28`, revision
  `0738d3c9f6993875e2f3dd0e8cc0bb4ae4440b4e` (SDL 2.28.5).
- `runtime/third_party/uam` from SwitchWakerHD, revision
  `44dc0e23e35ed10495cea7c6866e7e5a3e3aba4d`, including its original LICENSE
  and PATCHES.md. Compiler Mesa symbols are prefixed to avoid SDL/EGL conflicts.

`apply.py --engine ENGINE --sdl SDL_SOURCE --sdk SDK` installs the generic
backend into the private engine copy and patches the private SDL source.
It checks patch compatibility and is safe to run twice. It does not modify the
installed SDK. `build_uam.py --source UAM --output BUILD --sdk SDK` builds the
compiler and creates `libretuned_uam.a` plus a local receipt.

The normal local `tools/native/switch/build.py` entry point accepts
`--renderer deko3d --deko-sdl-source SDL_SOURCE --deko-uam-source UAM` alongside
its existing private build inputs. It applies the patches, builds the compiler,
and configures the host. OpenGL remains the default.

For a manually configured private host build, use:

```text
-DRETUNED_SWITCH_DEKO=ON
-DRETUNED_SDL_SOURCE=SDL_SOURCE
-DRETUNED_UAM_SOURCE=UAM
-DRETUNED_UAM_LIBRARY=BUILD/libretuned_uam.a
```

Keep the existing private title-link configuration. Generated game code, title
archives, ROM content, texture packs, runtime caches, and playable test NROs
must not be included in a public host/source package.

## Validation

The integration has reached native title and Fire Temple rendering in Ryujinx
on macOS. This establishes an emulator integration milestone, not physical
Switch compatibility, complete visual parity, or release readiness. Cold shader
compilation still causes stalls; warm-cache performance needs separate checks.
Controller configuration belongs to the emulator; it is not part of the cache.

Run the pure scissor partition test with a host C++17 compiler:

```sh
c++ -std=c++17 tests/switch/deko_scissor.cpp -o /tmp/retuned-deko-scissor
/tmp/retuned-deko-scissor
python3 -m unittest discover -s tests/switch -p test_deko_cache.py
```

The source helpers contain no generated title shaders. Backend code and patches
retain the engine's GPL-2.0-or-later terms. SDL alterations retain SDL's zlib
notice; uam and its imported compiler sources retain their original notices.

### Opening-sequence performance

The native texture view already carries a verified content hash. Reuse it when
available rather than scanning the texture bytes on every draw. Shader modules
are looked up by exact canonical source in memory; SHA-256 still identifies and
validates persistent DKSH entries. The tested file-selection scene fell from
about 184 ms to 33 ms per frame in Astris after removing the repeated work.

Optional local profiling is enabled at launch by
`sdmc:/switch/oot3dre/profile-renderer.flag`. It reports native draw/hash/lookup
costs and GPU submission waits. Leave the marker absent for normal launches.

Raw NRO loading in the tested emulator did not retain a host shader cache. A
private application NSP with a stable program identity did create and retain
that cache. This is separate from the app's DKSH cache: the emulator still has
to translate Switch shaders/pipelines for the host GPU. New variants can incur
first-use compilation. Emulator results do not establish physical Switch
performance. Private playable test packages and their caches are not release
artifacts.


## Switch Settings audit

The deko3d backend registers the shared Settings window and persistence port.
Minus opens Settings; the menu starts with controller navigation enabled.
Text and controller navigation have been verified in Astris.

- Keep language, menu size, controller mappings, ReFramed game controls, camera,
  motion, HUD, dialogue weight, quality of life, audio, and save states.
- Keep custom-texture enable/reload and status for the SD-card folder configured
  by desktop preparation. No desktop folder chooser is provided on Switch.
- Hide desktop display modes/resolutions, desktop graphics presets, AA/upscaler
  controls, advanced lighting/material effects, texture dumping, and touch.
- Android save-provider and adaptive-memory controls remain Android-only.
- Settings remain local to this test. Emulator configuration is separate.

Do not interpret visible native game controls as physical Switch performance
qualification. Check their behavior and persistence in emulation before handoff.


Switch frame-rate policy: new SD setups default to 30 FPS; the menu offers only
30 FPS and experimental interpolated 60 FPS. Saved 60 FPS choices remain valid;
saved 90 FPS or uncapped modes fall back to 30 FPS on startup.

Custom-pack staging accepts `--mobile-textures` and copies the supplied directory
without flattening it to `switch/oot3dre/textures`. Use the **mobile version of
Henriko's texture pack** for Switch, rather than the desktop pack, to reduce
memory use. The pack is optional and must be supplied separately by the user.

The deko backend supports asynchronous replacement loading, legacy Citra hashes,
bounded texture caches, and striped uploads for large images. Replacement uploads
and gameplay have been verified in Astris; the owner confirmed the corrected test
works well. This does not establish performance or memory stability on hardware.
See the [Switch setup guide](../../../../documentation/Switch-setup.md).
