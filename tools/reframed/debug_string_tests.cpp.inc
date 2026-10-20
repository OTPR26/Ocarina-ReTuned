void TestReframedDebugString() {
    NativeA32Memory memory;
    std::string error;
    Require(memory.MapRegion({"debug", 0x1000, 0x1000, true, false, {}}, &error), error);
    Require(memory.Write32(0x1FFC, 0x74736574), "write exact-length debug text");
    NativeA32CtrHostServices host;
    const oot3d::recomp::a32::Registry registry{};
    NativeA32Process process(registry, host);
    NativeA32HostContext context{process, 0};
    GuestState state{};
    state.r[0] = 0x1FFC;
    state.r[1] = 4;
    Require(host.HandleSvc(0x3D, state, memory, context).Action == NativeA32HostAction::Resume &&
            state.r[0] == 0 && host.SvcEvents().back().Name == "OutputDebugString:test",
            "debug string accepts a buffer without a trailing terminator");
    state.r[0] = 0xFFFFFFFF;
    state.r[1] = 0;
    Require(host.HandleSvc(0x3D, state, memory, context).Action == NativeA32HostAction::Resume && state.r[0] == 0,
            "empty debug string does not dereference its pointer");
    state.r[0] = 0x1FFC;
    state.r[1] = 5;
    Require(host.HandleSvc(0x3D, state, memory, context).Action == NativeA32HostAction::Wait,
            "debug string rejects an unmapped byte");
    state.r[0] = 0x1000;
    state.r[1] = 0x1000;
    Require(host.HandleSvc(0x3D, state, memory, context).Action == NativeA32HostAction::Resume &&
            host.SvcEvents().back().Name.size() == std::string("OutputDebugString:").size() + 1024,
            "debug history caps captured text");
}
