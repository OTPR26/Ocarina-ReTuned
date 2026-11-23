# Hosted builds

Use **Additional platform hosts** for iOS, tvOS, Windows ARM64, and Switch
runtime components. Select one platform per manual run. Nothing runs on push,
pull request, a schedule, or a release event. Existing Android, Mac, Windows
x64, and Linux workflows remain available separately.

The workflow uses standard hosted runners and requires this repository to be
public before building. It has a single concurrency group, 90-minute Apple /
Windows limits, a 60-minute Switch limit, and three-day artifact retention.
Compiler caches are limited to 1 GB per platform. Dependency caches contain
only public build dependencies. Do not rerun all platforms to fix one failure.

## Data boundary

Actions receives source and public dependencies only. Never add ROMs, prepared
game modules, saves, textures, signing keys, provisioning profiles, or device
backups as workflow inputs, secrets, caches, or artifacts.

Apple outputs are unsigned host bundles. Switch outputs are neutral link
components: the runner does not link a playable NRO or NSP. A user-owned ROM
and any personal signing identity still stay on the user's preparation machine.
Windows outputs are ARM64 host binaries and dependency notices. These are build
components, not automatically approved release downloads; preparation tools,
source/license closure, platform checks, and release audits still apply.

## Local cleanup

Keep local dependencies until a clean hosted build of the same target passes,
its artifact is downloaded and audited, and any private preparation or device
installation path no longer depends on that directory. Record the run, exact
source revision, artifact digest, and replacement procedure before deletion.
Do not remove Apple's SDKs if this Mac is still used to prepare/sign private
Apple apps, or the Switch SDK if private Switch preparation still needs it.

## Choosing a build

| Target | Workflow | Selection |
| --- | --- | --- |
| Android host | `android-native-host.yml` | No matrix |
| Android APK | `android-native-app.yml` | Reuse the successful host run and exact revision |
| Mac | `native-arm64.yml` | `platform=macos` |
| Windows x64 | `windows-portable.yml` | No matrix |
| Linux x64 / ARM64 | `desktop-native.yml` | `platform=linux` or `linux-arm64` |
| iOS / tvOS / Windows ARM64 / Switch components | `remaining-hosts.yml` | Select exactly one platform |

Use the existing release download when that platform has not changed. Avoid the
older workflows' `both` selection when only one target needs rebuilding.

To replace a removed local host cache, run the corresponding workflow at the
reviewed source revision, download its successful artifact, and repeat the
release asset and identity audits before staging it. Artifacts expire after
three days in the additional-host workflow; the checked-in recipe and pinned
public dependencies remain available to rebuild them. A successful compilation
does not replace device testing or the final release audit.
