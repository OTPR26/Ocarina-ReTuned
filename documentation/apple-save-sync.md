# Apple save sync

Mac, iOS and tvOS share the same CloudKit private-database bridge. Local play
works without iCloud. CloudKit is disabled at build time unless
`RETUNED_ICLOUD_CONTAINER` is set to the container authorized by the signing
profile. No container belonging to another app is used as a fallback.

Enable CloudKit on the explicit `io.github.otpr26.ocarinaretuned` app identifier
and assign the same container on all three platforms. Regenerate each platform's
provisioning profile. Use the same development or production environment on
all test devices; those databases are separate. Production needs the record
schema deployed before release. Only the current user's private database is used.

`ReTunedSaveBundle` has `contents` (Bytes), `digest` (String), and `schema` (Int64)
fields. Record `oot3d-usa-saves-v1` contains only the supported USA save files:
`save00.bin`–`save05.bin` and `system.dat`. No savestates, ROMs, title modules,
textures, graphics preferences or controller profiles are synchronized.

The bridge snapshots after a successful save-archive commit. Cloud operations run
on a serial background queue. Remote copies can only be applied before gameplay;
previous local saves are retained in a sibling backup directory. Downloads are
validated and staged before replacing the save directory. Cache eviction does
not delete cloud progress. Different local and cloud progress requires an
explicit choice in startup Settings → General. Concurrent cloud writes are
rejected through the record change tag rather than silently overwritten.

Create local entitlements with `prepare_cloud_entitlements.py`, which rejects
wildcard profiles, wrong app IDs and unauthorized containers. Signing files stay
private. Mac packaging accepts `--identity`, `--entitlements`, and `--profile`;
The native runtime must be the Mac bundle’s main executable so macOS can match
its iCloud entitlements to the provisioning profile. Public
unsigned builds need users' own matching signing and container configuration.

## Verification

Run `tests/save_sync.cpp` for merge/conflict decisions and supported paths.
On macOS, compile `tests/save_sync_files.mm` with ARC, Foundation, CloudKit and
Security for synthetic save validation, backup, restoration and symlink checks.
No real saves are required. SDK syntax checks do not replace a signed live sync
test between physical devices. Check offline play, first upload, restore on a
second device, competing edits, account changes and cache eviction before
claiming device sync verified.
