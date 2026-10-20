void TestReframedHidWrites() {
    for (const bool allowWrites : {false, true}) {
        NativeA32Memory memory;
        std::string error;
        Require(memory.MapRegion({"hid_tls",0x1FF82000,0x1000,true,false,{}},&error),error);
        NativeA32CtrHostConfig config;
        config.WritableHidSharedMemory = allowWrites;
        NativeA32CtrHostServices host(config);
        const oot3d::recomp::a32::Registry registry{};
        NativeA32Process process(registry,host);
        NativeA32HostContext context{process,0};
        GuestState state{};state.thread_pointer=0x1FF82000;
        constexpr uint32_t command=0x1FF82080;
        Require(memory.Write32(0x1FF82400,0x3A767273) && memory.Write8(0x1FF82404,0),"srv name");
        state.r[1]=0x1FF82400;
        Require(host.HandleSvc(0x2D,state,memory,context).Action==NativeA32HostAction::Resume,"srv open");
        const auto srv=state.r[1];
        Require(memory.Write32(command,0x00050100) && memory.Write32(command+4,0x3A646968) &&
                memory.Write32(command+8,0x52455355) && memory.Write32(command+12,8),"hid request");
        state.r[0]=srv;
        Require(host.HandleSvc(0x32,state,memory,context).Action==NativeA32HostAction::Resume,"hid session");
        uint32_t session=0,shared=0;
        Require(memory.Read32(command+12,&session) && memory.Write32(command,0x000A0000),"hid handles request");
        state.r[0]=session;
        Require(host.HandleSvc(0x32,state,memory,context).Action==NativeA32HostAction::Resume &&
                memory.Read32(command+12,&shared),"hid handles");
        state.r[0]=shared;state.r[1]=0x10002000;state.r[2]=1;state.r[3]=0x10000000;
        Require(host.HandleSvc(0x1F,state,memory,context).Action==NativeA32HostAction::Resume,"hid map");
        Require(memory.Write16(0x100020C8,222)==allowWrites,"synthetic touch access is profile-specific");
        Require(!memory.Write32(0x10003000,0),"synthetic touch cannot escape the HID mapping");
    }
}
