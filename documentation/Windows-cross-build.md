# Windows builds on an Apple silicon Mac

Preview 0.2.0's Windows x64 and ARM64 hosts use LLVM-MinGW 20261006
(UCRT, Clang 23.1.3) and vcpkg revision
`ef7dbf94b9198bc58f45951adcf1f041fcbc5ea0`.
Use the official LLVM-MinGW macOS universal archive, bootstrap the pinned vcpkg
checkout, and check out TriAevum runtime revision
`17218b0cfdb944645bb5cde5249f313dca7e53ce` in a separate source directory.

```sh
python3 tools/native/build_windows_cross.py \
  --arch arm64 --engine /path/to/runtime --llvm /path/to/llvm-mingw \
  --vcpkg /path/to/vcpkg --work /path/to/build-output --jobs 2
```

Use `--arch x64` for Windows x64. The script applies the shared ReTuned patches,
installs the pinned static dependencies, and links the neutral host. It needs no
ROM or generated game module. shaderc is linked statically; the matching Vulkan
loader DLL remains a runtime dependency. The supplied overlays preserve the
upstream sources and dependency notices.

The title module and host must use the same LLVM-MinGW ABI. Ship a matching
preparation toolchain, Python runtime, dependency notices, and `preparation-abi.json`
with a SHA-256 digest of the final executable. A cross-build does not validate
Windows GPU drivers or native gameplay.
