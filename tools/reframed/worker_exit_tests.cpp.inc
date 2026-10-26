void TestWorkerExitWhilePrimaryWaits() {
    const auto registry = MakeTestRegistry();
    TestHostServices services;
    Oot3dNativeGame::NativeA32Process process(registry, services);
    const std::array<uint8_t, 0x20> code{};
    std::string error;
    Expect(process.MapRegion({"text", kEntry, code.size(), false, true, code}, &error),
           "map worker-exit text");
    Expect(process.MapRegion({"data", kData, 0x100U, true, false, {}}, &error),
           "map worker-exit data");
    Expect(process.CreatePrimaryThread(
               {kEntry, kStack, 0x1000U, kTls, 0x1000U, 0, 0, 0, 0, 48U}, &error),
           "create waiting primary");
    Expect(process.Run().Kind == Oot3dNativeGame::NativeA32ProcessRunKind::Waiting,
           "primary must wait before movie worker exits");
    const auto worker = process.CreateThread(
        {kEntry + 0x10U, 0, kData + 0x100U, 0, 0, 24U}, &error);
    Expect(worker.has_value(), "create movie worker");
    const auto result = process.Run();
    Expect(process.ThreadStatus(*worker) == Oot3dNativeGame::NativeA32ThreadStatus::Terminated,
           "movie worker must exit");
    Expect(result.Kind == Oot3dNativeGame::NativeA32ProcessRunKind::Waiting,
           "exiting movie worker must not terminate a waiting game");
    Expect(process.Run().Kind == Oot3dNativeGame::NativeA32ProcessRunKind::Waiting,
           "game must remain waiting until the event completes");
    Expect(process.ResumePrimaryThread(std::nullopt, &error), "resume game after worker exit");
    Expect(process.Run().Kind == Oot3dNativeGame::NativeA32ProcessRunKind::Terminated &&
               services.StatePersisted,
           "only the final thread exit may terminate the game");
}
