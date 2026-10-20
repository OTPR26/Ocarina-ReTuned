void TestReframedIrst() {
    NativeA32Memory memory;
    std::string error;
    Require(memory.MapRegion({"irst_test_tls", 0x1FF82000, 0x1000, true, false, {}}, &error), error);
    NativeA32CtrHostServices host;
    const oot3d::recomp::a32::Registry registry{};
    NativeA32Process process(registry, host);
    NativeA32HostContext context{process, 0};
    GuestState state{};
    state.thread_pointer = 0x1FF82000;
    constexpr uint32_t command = 0x1FF82080;
    constexpr uint32_t nameAddress = 0x1FF82400;
    Require(memory.Write32(nameAddress, 0x3A767273), "write srv port");
    Require(memory.Write8(nameAddress + 4, 0), "terminate srv port");
    state.r[1] = nameAddress;
    Require(host.HandleSvc(0x2D, state, memory, context).Action == NativeA32HostAction::Resume,
            "connect IRRST test service manager");
    const auto srv = state.r[1];
    Require(memory.Write32(command, 0x00050100) &&
            memory.Write32(command + 4, 0x723A7269) &&
            memory.Write32(command + 8, 0x00007473) &&
            memory.Write32(command + 12, 6), "write IRRST service request");
    state.r[0] = srv;
    Require(host.HandleSvc(0x32, state, memory, context).Action == NativeA32HostAction::Resume,
            "open IRRST service");
    uint32_t session = 0;
    Require(memory.Read32(command + 12, &session) && session, "IRRST session");
    Require(memory.Write32(command, 0x00010000), "write IRRST handles request");
    state.r[0] = session;
    Require(host.HandleSvc(0x32, state, memory, context).Action == NativeA32HostAction::Resume,
            "IRRST handles response");
    uint32_t shared = 0, event = 0, response = 0;
    Require(memory.Read32(command, &response) && response == 0x00010043 &&
            memory.Read32(command + 12, &shared) && shared &&
            memory.Read32(command + 16, &event) && event, "IRRST handle layout");
    Require(memory.Write32(command, 0x00020080), "IRRST initialize request");
    state.r[0] = session;
    Require(host.HandleSvc(0x32, state, memory, context).Action == NativeA32HostAction::Resume,
            "IRRST initialization");
    state.r[0] = shared;
    state.r[1] = 0x10000000;
    state.r[2] = 1;
    state.r[3] = 0x10000000;
    Require(host.HandleSvc(0x1F, state, memory, context).Action == NativeA32HostAction::Resume,
            "map IRRST readonly shared memory");
    for (uint32_t i = 0; i < 17; ++i) {
        host.AdvanceSystemTicks(100);
        Require(host.WriteIrstSample(memory, 154, -100, i % 2 ? 0U : 1U << 14U),
                "publish IRRST sample");
        uint32_t index = 0, held = 0;
        uint16_t x = 0, y = 0;
        Require(memory.Read32(0x10000010, &index) && index == (i + 1) % 8,
                "IRRST ring index wraps");
        const uint32_t entry = 0x10000018 + index * 16;
        Require(memory.Read32(entry, &held) && held == (i % 2 ? 0U : 1U << 14U) &&
                memory.Read16(entry + 12, &x) && x == 154 &&
                memory.Read16(entry + 14, &y) && static_cast<int16_t>(y) == -100,
                "IRRST axes and shoulder states");
        uint64_t tick = 0, previous = 0;
        Require(memory.Read64(0x10000000, &tick, nullptr) && memory.Read64(0x10000008, &previous, nullptr) && tick != previous,
                "IRRST update timestamps stay distinguishable");
    }
    Require(!memory.Write32(0x10000000, 0), "IRRST mapping remains guest readonly");
}
