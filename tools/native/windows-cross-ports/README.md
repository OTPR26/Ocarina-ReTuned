# Windows cross-build overlays

These recipes are from vcpkg revision
`ef7dbf94b9198bc58f45951adcf1f041fcbc5ea0`, under the included Microsoft MIT license.

- SPIRV-Tools adds the missing standard `<iterator>` include for current Clang.
- shaderc omits its optional command-line-tool deployment when building on a
  non-Windows host. The shader compiler library remains enabled.

The source version, upstream archive digests, licenses, and original patches are
retained in each port recipe.
