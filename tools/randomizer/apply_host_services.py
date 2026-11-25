#!/usr/bin/env python3
"""Add opt-in service callbacks to an explicitly selected private engine tree."""
from pathlib import Path
import argparse

BASE = Path('tools/oot3d/native_game_runtime')


def replace(text, anchor, replacement):
    if replacement in text:
        return text
    if text.count(anchor) != 1:
        raise ValueError('Native host context changed; refusing partial patch')
    return text.replace(anchor, replacement)


def apply(root):
    paths = [root / BASE / name for name in ('oot3d_native_a32_ctr_host.h',
             'oot3d_native_a32_ctr_host.cpp', 'oot3d_native_a32_ctr_host_fs.cpp')]
    header, host, filesystem = [path.read_text() for path in paths]
    anchor = 'struct NativeA32CtrHostConfig {\n'
    header = replace(header, anchor, anchor + '''    // Empty for ordinary games. Bound only by the isolated randomizer runner.
    std::function<bool(uint32_t, oot3d::recomp::a32::GuestState&, NativeA32Memory&)> RandomizerSvc;
    std::function<std::optional<bool>(const std::filesystem::path&, uint64_t, std::span<const uint8_t>)> WriteRandomizerSave;
''')
    anchor = '    switch (immediate) {\n    case 0x01:'
    host = replace(host, anchor, '''    if (immediate == 0xfff401 || immediate == 0xfff402 ||
        immediate == 0xfff403 || immediate == 0xfff404 ||
        immediate == 0xfff405 || immediate == 0xfff40b) {
        event.Name = "RandomizerService";
        try {
            if (!mConfig.RandomizerSvc || !mConfig.RandomizerSvc(immediate, state, memory))
                throw std::runtime_error("Randomizer service is not configured");
            event.Handled = true;
            mSvcEvents.push_back(std::move(event));
            return {NativeA32HostAction::Resume};
        } catch (const std::exception& error) {
            mSvcEvents.push_back(std::move(event));
            return {NativeA32HostAction::Fault, std::nullopt, 0U, error.what()};
        }
    }
''' + anchor)
    anchor = '    if (immediate == 0xfff401 || immediate == 0xfff402 ||'
    host = replace(host, anchor, '''    // The proof runtime queries Citra's identification extension. This is a
    // native host, so report false without claiming other system-info support.
    if (mConfig.RandomizerSvc && immediate == 0x2a &&
        state.r[1] == 0x20000 && state.r[2] == 0) {
        state.r[0] = 0; state.r[1] = 0; state.r[2] = 0;
        event.Name = "NativeRandomizerEnvironment";
        event.Handled = true;
        mSvcEvents.push_back(std::move(event));
        return {NativeA32HostAction::Resume};
    }
''' + anchor)
    anchor = '            bool success = false;\n            uint32_t written = 0U;'
    filesystem = replace(filesystem, anchor, """            if (mConfig.WriteRandomizerSave) {
                try {
                    const auto handled = mConfig.WriteRandomizerSave(file.FilePath, offset, bytes);
                    if (handled.has_value()) {
                        if (!*handled) return fail(kFsBackendFailure, "randomizer-save-rejected", offset, length);
                        file.FileSize = offset + length;
                        return reply(kFileWriteResponse, "Write", length, descriptor, address);
                    }
                } catch (const std::exception&) {
                    return fail(kFsBackendFailure, "randomizer-save-state-failed", offset, length);
                }
            }
""" + anchor)
    setup_path=root/BASE/'oot3d_native_a32_window_setup.cpp'
    setup=setup_path.read_text()
    # The ordinary bridge must never restore cloud saves into a seed profile.
    if 'RetunedSaveSyncConfigure' in setup:
        setup=replace(setup,'RetunedSaveSyncConfigure(saveDataDirectory.string().c_str());',
            'RetunedSaveSyncConfigure(hostConfig.RandomizerSvc ? nullptr : saveDataDirectory.string().c_str());')
        setup=replace(setup,'hostConfig.SaveDataCommitted=[] {RetunedSaveSyncCommitted();};',
            'if(!hostConfig.RandomizerSvc) hostConfig.SaveDataCommitted=[] {RetunedSaveSyncCommitted();};')
    # Check all anchors before writing any file; preserve unrelated engine work.
    for path, content in zip(paths, (header, host, filesystem)):
        if path.read_text() != content:
            path.write_text(content)
    if setup_path.read_text()!=setup:setup_path.write_text(setup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine.resolve())
