# Standalone deko3d probe

This isolated homebrew program loads locally compiled DKSH modules, renders to a
256 × 256 RGBA8 offscreen target, and compares GPU readback with CPU expectations.
It does not load the game, a ROM, or saves. It does not compile shaders at runtime.

## Build inputs

Use the official devkitPro Switch toolchain, libnx, and the debug deko3d library
(`libdeko3dd.a`). Supply `RETUNED_PROBE_FIXTURES` as an absolute directory containing
an independently generated `probe_fixtures.h`. The header describes:

- `kModules`: basenames of validated DKSH files, with `kModuleCount`;
- `kControlVertex`: index of the synthetic full-screen vertex shader;
- `kTests`: `ProbeTest { name, fragment, mode, integer0 }` records;
- `kMathValues[64]`: signed input values for the arithmetic shader.

Modes 0, 1, and 2 expect red, white, and `(64,128,192,255)` throughout the rasterized target.
Mode 3 compares packed signed division-by-nine and signed `(n/2)%2` results over
128 pixels. `integer0` selects an integer texture for fragment slot zero.
Optional active fixtures define `RETUNED_PROBE_UNIFORM_FIXTURES` and add
`uniforms`, `uniformCount`, and `expected[4]` to `ProbeTest`. Each uniform write
contains a byte `offset` and an unsigned 32-bit `value`. Mode 4 uses the explicit
expected RGBA value. The uniform block is reset between cases.

Stage the matching modules at `sdmc:/switch/retuned-deko-probe/modules/`.
Results are flushed to `sdmc:/switch/retuned-deko-probe/result.txt`; a successful
run ends with `status=PASS`. A build alone is not a rendering pass.

```sh
cmake -S tools/native/switch/deko_probe -B /absolute/private/probe-build \
  -G Ninja -DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/cmake/Switch.cmake" \
  -DRETUNED_PROBE_FIXTURES=/absolute/private/fixtures
cmake --build /absolute/private/probe-build
```

Keep ROM-derived fixtures, DKSH files, generated headers, and diagnostic outputs
private. They are deliberately not included beside this source.

## Qualification limits

Module initialization does not execute a shader. The current fixture set loads
70 modules but draws only selected fragment cases with a synthetic vertex shader.
The original PICA vertex shader is initialized, not semantically validated.
The five baseline family tests use zero uniforms. Four additional cases exercise
one/eight lights, global ambient color, and a procedural color LUT. They do not
qualify all lighting, shadow, fog, or procedural-texture operations. This is not
full renderer or gameplay validation.

The combined family originally triggered a host Metal GPU hang in Ryujinx.
Replacing dynamic indexing of two by-value local TEV arrays with explicit
six-stage selections in `deko_cache.py` resolves the tested failure. No lighting
or texture feature is disabled. The converter's cache policy changed to invalidate
old compiled records. The probe also sizes per-warp scratch memory from DKSH
requirements and binds the lighting sampler to a floating-point texture descriptor.

The corrected Mac emulator run passes all 13 readback checks: every pixel in twelve
256 × 256 color targets and all 128 arithmetic cases. Saved DKSH family records
reload with zero compiler calls. Eden's separate initialization failure, also seen
with the unmodified official example, remains unresolved. No physical Switch result
is available. Do not treat this probe as evidence of improved full-game performance.
