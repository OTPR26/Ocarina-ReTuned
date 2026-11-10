#!/usr/bin/env python3
"""Backport the Android shared-page clock to the pinned native runtime."""

from pathlib import Path


def replace_once(source, before, after, description):
    if source.count(after) == 1:
        return source
    if source.count(before) != 1:
        raise ValueError(f"Android clock {description} context changed")
    return source.replace(before, after, 1)


def apply(root):
    runtime = Path(root) / 'tools/oot3d/native_game_runtime'
    image = runtime / 'oot3d_native_a32_process_image.cpp'
    frame = runtime / 'oot3d_native_a32_window_frame.cpp'
    header = runtime / 'oot3d_native_a32_clock.h'
    header_bytes = (Path(__file__).parent / 'android/oot3d_native_a32_clock.h').read_bytes()
    if header.exists() and header.read_bytes() != header_bytes:
        raise ValueError('Android clock header already exists with different content')

    image_text = image.read_text(encoding='utf-8')
    image_text = replace_once(image_text,
        '#include "oot3d_native_a32_process_image.h"\n',
        '#include "oot3d_native_a32_process_image.h"\n#include "oot3d_native_a32_clock.h"\n',
        'image include')
    image_text = replace_once(image_text,
        '''        for (const auto& region : manifest.SystemRegions) {
            std::string mapError;
            if (!process.MapRegion({region.Name, region.Address,
                                    region.MappedSize, region.Writable,
                                    region.Executable, region.InitialBytes},
''',
        '''        for (const auto& region : manifest.SystemRegions) {
            std::string mapError;
            auto initialBytes = region.InitialBytes;
#if defined(__ANDROID__)
            if (region.Name == "ctr_shared_page" && region.Address == 0x1FF81000U) {
                const auto localMs = HostLocalClockMillisecondsSince1900();
                if (localMs) InitializeSharedPageClock(initialBytes, *localMs);
            }
#endif
            if (!process.MapRegion({region.Name, region.Address,
                                    region.MappedSize, region.Writable,
                                    region.Executable, initialBytes},
''', 'process mapping')

    frame_text = frame.read_text(encoding='utf-8')
    frame_text = replace_once(frame_text,
        '#include "oot3d_native_room_shadow_shell.h"\n',
        '#include "oot3d_native_room_shadow_shell.h"\n#if defined(__ANDROID__)\n#include "oot3d_native_a32_clock.h"\n#endif\n',
        'frame include')
    frame_text = replace_once(frame_text,
        '''  auto &dspHle = *dspHleStorage;
#if defined(TRIAEVUM_DEVELOPER_TOOLS)
''',
        '''  auto &dspHle = *dspHleStorage;
#if defined(__ANDROID__)
  // The emulated tick counter advances with guest frames, not wall time. Rebase
  // before every refresh, including the first frame after resume or state load.
  // The guest is stopped here, and the shared page remains guest read-only.
  constexpr uint32_t sharedPage = 0x1FF81000U;
  const auto localMs = Oot3dNativeGame::HostLocalClockMillisecondsSince1900();
  // Retain the last valid reference if the host clock or shared page is unavailable.
  if (localMs) Oot3dNativeGame::PublishSharedPageClock(
          [&](uint32_t* counter) { return process.Memory().Read32(sharedPage, counter); },
          [&](uint32_t offset, std::span<const uint8_t> bytes) {
            return process.Memory().WriteHostBytes(sharedPage + offset, bytes);
          }, *localMs, hostServices.SystemTicks());
#endif
#if defined(TRIAEVUM_DEVELOPER_TOOLS)
''', 'frame refresh')

    # Validate every source context and any existing header before writing files.
    image.write_text(image_text, encoding='utf-8')
    frame.write_text(frame_text, encoding='utf-8')
    if not header.exists():
        header.write_bytes(header_bytes)
