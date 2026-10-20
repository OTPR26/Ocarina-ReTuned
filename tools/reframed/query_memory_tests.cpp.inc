void TestReframedQueryMemory() {
    NativeA32Memory memory;
    std::string error;
    Require(memory.MapRegion({"code", 0x1000, 0x2000, false, true, {}}, &error), error);
    Require(memory.MapRegion({"shared_memory:test", 0x10001000, 0x1000, false, false, {}}, &error), error);
    NativeA32CtrHostServices host;
    const oot3d::recomp::a32::Registry registry{};
    NativeA32Process process(registry, host);
    NativeA32HostContext context{process, 0};
    GuestState state{};
    auto query = [&](uint32_t address, uint32_t base, uint32_t size, uint32_t perm, uint32_t kind) {
        state.r[2] = address;
        state.r[5] = 0xFFFFFFFF;
        Require(host.HandleSvc(0x02, state, memory, context).Action == NativeA32HostAction::Resume,
                "QueryMemory resumes");
        Require(state.r[0] == 0 && state.r[1] == base && state.r[2] == size &&
                state.r[3] == perm && state.r[4] == kind && state.r[5] == 0,
                "QueryMemory returns exact region and register ABI");
    };
    query(0, 0, 0x1000, 0, 0);
    query(0x1000, 0x1000, 0x2000, 5, 4);
    query(0x2FFF, 0x1000, 0x2000, 5, 4);
    query(0x3000, 0x3000, 0x0FFFE000, 0, 0);
    query(0x10000000, 0x3000, 0x0FFFE000, 0, 0);
    query(0x10001000, 0x10001000, 0x1000, 1, 6);
    query(0x10002000, 0x10002000, 0x2FFFE000, 0, 0);
    query(0x40000000, 0x40000000, 0xC0000000, 0, 1);
    query(0xFFFFFFFF, 0x40000000, 0xC0000000, 0, 1);
    Require(memory.MapRegion({"heap", 0x10000000, 0x1000, true, false, {}}, &error), error);
    query(0x10000001, 0x10000000, 0x1000, 3, 5);
    query(0xFFFF, 0x3000, 0x0FFFD000, 0, 0);
}
