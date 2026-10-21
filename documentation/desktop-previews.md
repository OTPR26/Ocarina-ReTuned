# Windows and Linux native previews

The Desktop native previews workflow builds Windows x64 and Linux x86_64
hosts from the pinned runtime with ReTuned's shared menus, controls and audio
changes. It stages only the host, bootstrap library, dependency closure,
controller mappings and notices. No private title, ROM, extracted game data,
textures or saves are supplied to CI.

The upstream translated vertex shader tables and precompiled title shader pack
are removed before compilation. The generic PICA decompiler instead consumes
the shaders in the user's locally prepared game data. Package staging rejects
the original upstream payloads in the actual native binary. This concerns GPU
shader preparation; game CPU code still uses a locally prepared native title.

These are development hosts, not complete first-run installers. They require a
matching private Windows/Linux title and launch profile prepared locally. The
Mac and Android title libraries cannot be reused across operating systems or
architectures. The private title CMake project supports desktop compilers; its
inputs and outputs must never be uploaded.

Release gates include a dependency/package audit, a real launch and gameplay
check, and a supported ROM-preparation path documented for new users. The
Setup dialog invokes the local ROM-preparation pipeline when its matching
toolkit is installed beside the host. Private Windows/Linux toolkits now carry
Python, Capstone and JSON headers; CMake, Ninja and the platform C++ compiler/SDK
remain prerequisites. Windows and Linux host builds and archive audits pass,
but full preparation and gameplay on those systems remain unverified. Do not
label these hosts as ready-to-play release packages before those gates pass.

Mac packaging checks every bundled ARM64 Mach-O binary's recorded minimum OS,
including libraries and any preparation toolkit. The default package target is
macOS 13.4. A dependency built for a newer OS rejects packaging, even if the main
executable targets 13.4. Rebuild that dependency for the supported target;
`--minimum-macos` can explicitly choose a higher minimum for a separate test
package. The package records the checked versions in `macos-deployment.json`.
An SDK version alone is not a minimum-OS or gameplay compatibility check.
