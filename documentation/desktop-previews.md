# Windows and Linux native previews

Local builds produce Windows x64 and Linux x86_64
hosts from the pinned runtime with ReTuned's shared menus, controls and audio
changes. It stages only the host, bootstrap library, dependency closure,
controller mappings and notices. No private title, ROM, extracted game data,
textures or saves are supplied in neutral host packages. GitHub Actions is not
used for final Preview builds.

The upstream translated vertex shader tables and precompiled title shader pack
are removed before compilation. The generic PICA decompiler instead consumes
the shaders in the user's locally prepared game data. Package staging rejects
the original upstream payloads in the actual native binary. This concerns GPU
shader preparation; game CPU code still uses a locally prepared native title.

The Preview archives combine the neutral host and local preparation toolkit.
First-run setup prepares a matching private title and launch profile from the
user's supported ROM. The
Mac and Android title libraries cannot be reused across operating systems or
architectures. The private title CMake project supports desktop compilers; its
inputs and outputs must never be uploaded.

Release gates include a dependency/package audit, a real launch and gameplay
check, and a supported ROM-preparation path documented for new users. The
Setup dialog invokes the local ROM-preparation pipeline when its matching
toolkit is installed beside the host. Windows includes a matching portable
compiler, CMake and Ninja alongside Python, Capstone and JSON headers. Linux
currently needs CMake, Ninja and a C++20 compiler with system headers. Full ROM
preparation and gameplay have passed on real Windows and Bazzite/Linux machines,
including controllers, HUD and dialogue; Linux audio has also been confirmed.
Final public resource, source, dependency and package audits remain release gates.
Private test fixtures and prepared game modules are not public release packages.
The separately documented ReFramed UI pack is an intentionally retained input;
it must not be described as containing no game-derived material.

Mac packaging checks every bundled ARM64 Mach-O binary's recorded minimum OS,
including libraries and any preparation toolkit. The default package target is
macOS 13.4. A dependency built for a newer OS rejects packaging, even if the main
executable targets 13.4. Rebuild that dependency for the supported target;
`--minimum-macos` can explicitly choose a higher minimum for a separate test
package. The package records the checked versions in `macos-deployment.json`.
An SDK version alone is not a minimum-OS or gameplay compatibility check.
The Mac CI preview explicitly targets macOS 15.0 for both compilation and
packaging, matching the recorded minimum of its audited dependency set on the
macOS 15 runner. This does not establish gameplay verification on every OS
version. A newer dependency requirement must still pass the package check.

## Linux audio runtime

SDL loads the PipeWire client and its plugins dynamically, so inspecting only
`ldd` output misses this dependency. Linux staging includes the client library,
PipeWire modules, SPA plugins and client configuration. Their transitive shared
libraries and distro copyright/source-version records are collected too. Missing
required client files stop packaging. No audio server is started by the app.

The launcher selects PipeWire when the user session exposes its default socket,
and preserves an explicit `SDL_AUDIODRIVER` selection. Bundled config/module/plugin
paths are relative to the package, with user overrides preserved. The extracted
archive passed an actual SDL stereo 48 kHz device-open check on Bazzite using
its bundled PipeWire and SPA modules. Graphics drivers and the user-session audio
server remain supplied by the operating system.
