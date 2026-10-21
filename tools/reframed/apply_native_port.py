#!/usr/bin/env python3
"""Add the Reframed profile, native C-stick service and scalar lowering support."""
from pathlib import Path
import argparse
import subprocess


def edit(path, before, after):
    source = path.read_text()
    if after in source:
        return
    if source.count(before) != 1:
        raise ValueError('Native translation context changed: ' + str(path))
    path.write_text(source.replace(before, after))


def apply_plugin_exports(engine):
    """Keep Windows ABI declarations consistent with the exported adapter definitions."""
    host = Path(engine) / 'tools/oot3d/native_game_runtime'
    plugin = host / 'triaevum_title_whole_aot_plugin.cpp'
    export = '#if defined(_WIN32)\n#define TRIAEVUM_TITLE_AOT_EXPORT __declspec(dllexport)\n#else\n#define TRIAEVUM_TITLE_AOT_EXPORT __attribute__((visibility("default")))\n#endif\n'
    source = plugin.read_text()
    if not source.startswith(export):
        if source.count(export) != 1:
            raise ValueError('Title adapter export context changed')
        plugin.write_text(export + '\n' + source.replace(export, '', 1))
    for name, program in (('triaevum_title_aot_abi.h', 'Oot3dDirectAotProgramV1'),
                          ('triaevum_title_whole_aot_abi.h', 'Oot3dWholeAotProgramV2')):
        edit(host / name, 'extern "C" const ' + program + ' *',
             'extern "C"\n#ifdef TRIAEVUM_TITLE_AOT_EXPORT\nTRIAEVUM_TITLE_AOT_EXPORT\n#endif\nconst ' + program + ' *')


def apply_translation_support(engine):
    """Generic ARM lowering and memory support, also used by preparation kits."""
    apply_plugin_exports(engine)
    root = Path(engine) / 'tools/oot3d/native_a32_runtime'
    edit(root / 'whole_aot_cpp.py',
         '    if unary in {0x0EB10B40, 0x0EB10BC0, 0x0EB40B40, 0x0EB40BC0}:',
         '    if unary in {0x0EB50B40, 0x0EB50BC0}:\n        return (raw & ((1 << 22) | (1 << 5) | 0xF)) == 0\n    if unary in {0x0EB10B40, 0x0EB10BC0, 0x0EB40B40, 0x0EB40BC0}:')
    runtime = root / 'upstream/recomp/a32_vfp_binary64.cpp'
    edit(runtime,
         '    switch (raw & kUnaryMask) {\n    case 0x0EB10B40U:',
         '    switch (raw & kUnaryMask) {\n    case 0x0EB50B40U:\n    case 0x0EB50BC0U:\n        return HasUnaryDoubleRegisters(raw) && (raw & 0xFU) == 0U;\n    case 0x0EB10B40U:')
    edit(runtime,
         '        case 0x0EB40B40U:\n        case 0x0EB40BC0U: {',
         '        case 0x0EB50B40U:\n        case 0x0EB50BC0U:\n        case 0x0EB40B40U:\n        case 0x0EB40BC0U: {')
    edit(runtime,
         '                ReadDouble(state, destination),\n                ReadDouble(state, right),\n                unary == 0x0EB40BC0U);',
         '                ReadDouble(state, destination),\n                (unary & 0x00010000U) != 0U ? 0ULL : ReadDouble(state, right),\n                (unary & 0x80U) != 0U);')


    edit(root / 'whole_aot_cpp.py',
         '    if unary in {0x0EB80BC0, 0x0EB70AC0}:',
         '    if unary in {0x0EB80B40, 0x0EB80BC0, 0x0EB70AC0}:')
    edit(runtime,
         '    case 0x0EB80BC0U:\n    case 0x0EB70AC0U:',
         '    case 0x0EB80B40U:\n    case 0x0EB80BC0U:\n    case 0x0EB70AC0U:')
    edit(runtime,
         '        case 0x0EB80BC0U:\n            result = F64FromSigned',
         '        case 0x0EB80B40U:\n            result = RoundFinite({0U, state.vfp[RightLane(raw)]}, {0U, 1U},\n                                 0, false, control, kBinary64);\n            break;\n        case 0x0EB80BC0U:\n            result = F64FromSigned')
    edit(root / 'whole_aot_cpp.py',
         '    elif unary in {0x0EB40A40, 0x0EB40AC0}:',
         '    elif unary in {0x0EB40A40, 0x0EB40AC0, 0x0EB50A40, 0x0EB50AC0}:')
    edit(root / 'whole_aot_cpp.py',
         """                f"    {_lane(destination)}, {_lane(right)},",\n                f"    {'true' if unary == 0x0EB40AC0 else 'false'});",""",
         """                f"    {_lane(destination)}, {'0U' if unary & 0x10000 else _lane(right)},",\n                f"    {'true' if unary & 0x80 else 'false'});",""")

    memory_header = Path(engine) / 'tools/oot3d/native_game_runtime/oot3d_native_a32_memory.h'
    edit(memory_header, '    size_t RegionCount() const;',
         '    struct RegionInfo { uint32_t BaseAddress, Size, Permissions, State; };\n    RegionInfo QueryRegion(uint32_t address) const;\n    size_t RegionCount() const;')
    query = Path(__file__).with_name('query_memory.cpp.inc').read_text()
    edit(memory_header.with_suffix('.cpp'), 'size_t NativeA32Memory::RegionCount() const {',
         query + '\nsize_t NativeA32Memory::RegionCount() const {')


def apply(engine):
    actual = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != '17218b0cfdb944645bb5cde5249f313dca7e53ce':
        raise ValueError('Unexpected native runtime revision')
    root = Path(engine) / 'tools/oot3d/native_a32_runtime'
    apply_translation_support(engine)

    profile = Path(engine) / 'tools/oot3d/ui_topscreen/oot3d_top_screen_mod_profile.h'
    edit(profile, '  Oot3d,\n  TopScreen,', '  Oot3d,\n  TopScreen,\n  Reframed,')
    source = profile.with_suffix('.cpp')
    edit(source, '  case Oot3dUiProfile::TopScreen:\n    return "topscreen";',
         '  case Oot3dUiProfile::Reframed:\n    return "reframed";\n  case Oot3dUiProfile::TopScreen:\n    return "topscreen";')
    edit(source, '  if (value == "topscreen") {',
         '  if (value == "reframed") {\n    *profile = Oot3dUiProfile::Reframed;\n    return true;\n  }\n  if (value == "topscreen") {')
    header = root.parent / 'native_game_runtime/oot3d_native_a32_ctr_host.h'
    edit(header, '    uint64_t SystemTicks() const;',
         '    bool WriteIrstSample(NativeA32Memory& memory, int16_t x, int16_t y, uint32_t buttons);\n    uint64_t SystemTicks() const;')
    edit(header, '    bool WriteHidSample(',
         '    NativeA32HostResult HandleIrstRequest(oot3d::recomp::a32::GuestState& state, NativeA32Memory& memory, uint32_t commandBuffer, NativeA32CtrSvcEvent event);\n    bool WriteHidSample(')
    host = header.with_suffix('.cpp')
    edit(host, 'serviceName == "ndm:u" || serviceName == "y2r:u")',
         'serviceName == "ndm:u" || serviceName == "y2r:u" || serviceName == "ir:rst")')
    edit(host, '        if (*sessionType == "client_session:hid:USER") {',
         '        if (*sessionType == "client_session:ir:rst") {\n            return HandleIrstRequest(state, memory, commandBuffer, std::move(event));\n        }\n        if (*sessionType == "client_session:hid:USER") {')
    query_svc = Path(__file__).with_name('query_memory_svc.cpp.inc').read_text()
    if 'case 0x02:' not in host.read_text():
        edit(host, '    case 0x08: {', query_svc + '    case 0x08: {')
    debug_svc = Path(__file__).with_name('debug_string_svc.cpp.inc').read_text()
    edit(host, '    case 0x39:', debug_svc + '    case 0x39:')
    if 'bool WritableHidSharedMemory' not in header.read_text():
        edit(header, 'struct NativeA32CtrHostConfig {',
             'struct NativeA32CtrHostConfig {\n    bool WritableHidSharedMemory = false;')
    edit(host, '                 (permissions & 2U) != 0,',
         '                 (permissions & 2U) != 0 || (mConfig.WritableHidSharedMemory && memoryBlock->Object->Type == "shared_memory:hid"),')
    setup = header.parent / 'oot3d_native_a32_window_setup.cpp'
    if 'hostConfig.WritableHidSharedMemory =' not in setup.read_text():
        edit(setup, '  hostConfig.SystemLanguage = languageSettings->SystemId();',
             '  hostConfig.WritableHidSharedMemory = launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed;\n  hostConfig.SystemLanguage = languageSettings->SystemId();')
    hid = header.parent / 'oot3d_native_a32_ctr_host_hid.cpp'
    addition = Path(__file__).with_name('irst_service.cpp.inc').read_text()
    edit(hid, '} // namespace Oot3dNativeGame', addition + '\n} // namespace Oot3dNativeGame')
    frame = header.parent / 'oot3d_native_a32_window_frame.cpp'
    if 'hostServices.WriteIrstSample(process.Memory()' not in frame.read_text():
        edit(frame, '  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(',
             '  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed &&\n      !hostServices.WriteIrstSample(process.Memory(), inputFrame.CStick.X, inputFrame.CStick.Y, inputFrame.Hid.Buttons)) {\n    throw std::runtime_error("Cannot publish Reframed C-stick input");\n  }\n  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(')

    tests = header.parent / 'oot3d_native_a32_ctr_host_tests.cpp'
    test_source = Path(__file__).with_name('irst_tests.cpp.inc').read_text()
    if 'void TestReframedIrst()' not in tests.read_text():
        edit(tests, 'int main() {', test_source + '\nint main() {\n    TestReframedIrst();')
    query_tests = Path(__file__).with_name('query_memory_tests.cpp.inc').read_text()
    if 'void TestReframedQueryMemory()' not in tests.read_text():
        edit(tests, 'int main() {', query_tests + '\nint main() {\n    TestReframedQueryMemory();')

    debug_tests = Path(__file__).with_name('debug_string_tests.cpp.inc').read_text()
    if 'void TestReframedDebugString()' not in tests.read_text():
        edit(tests, 'int main() {', debug_tests + '\nint main() {\n    TestReframedDebugString();')
    hid_tests = Path(__file__).with_name('hid_write_tests.cpp.inc').read_text()
    if 'void TestReframedHidWrites()' not in tests.read_text():
        edit(tests, 'int main() {', hid_tests + '\nint main() {\n    TestReframedHidWrites();')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
