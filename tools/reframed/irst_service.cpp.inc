// The mod uses New 3DS IRRST shared memory for its C-stick input.
NativeA32HostResult NativeA32CtrHostServices::HandleIrstRequest(
    oot3d::recomp::a32::GuestState& state, NativeA32Memory& memory,
    uint32_t commandBuffer, NativeA32CtrSvcEvent event) {
    const uint32_t command = event.Detail >> 16U;
    bool written = false;
    if (event.Detail == 0x00010000U) {
        auto shared = std::make_shared<KernelObject>();
        shared->Type = "shared_memory:ir:rst";
        shared->FileSize = 0x1000U;
        const uint32_t sharedHandle = CreateHandle(shared);
        const uint32_t eventHandle = CreateHandle("event:ir:rst");
        written = memory.Write32(commandBuffer, 0x00010043U) &&
                  memory.Write32(commandBuffer + 4U, 0U) &&
                  memory.Write32(commandBuffer + 8U, 0x04000000U) &&
                  memory.Write32(commandBuffer + 12U, sharedHandle) &&
                  memory.Write32(commandBuffer + 16U, eventHandle);
        if (!written) {
            CloseHandle(sharedHandle);
            CloseHandle(eventHandle);
        }
    } else if (event.Detail == 0x00020080U || event.Detail == 0x00030000U) {
        written = memory.Write32(commandBuffer, (command << 16U) | 0x40U) &&
                  memory.Write32(commandBuffer + 4U, 0U);
    }
    if (written) {
        state.r[0] = 0U;
        event.Handled = true;
        mSvcEvents.push_back(std::move(event));
        return {NativeA32HostAction::Resume};
    }
    mSvcEvents.push_back(std::move(event));
    return {NativeA32HostAction::Wait};
}

bool NativeA32CtrHostServices::WriteIrstSample(
    NativeA32Memory& memory, int16_t x, int16_t y, uint32_t buttons) {
    for (const auto& handle : mHandles) {
        if (handle.Object->Type != "shared_memory:ir:rst" ||
            !handle.Object->MappedAddress.has_value()) continue;
        const uint32_t base = *handle.Object->MappedAddress;
        uint32_t index = 0;
        if (!memory.Read32(base + 16U, &index)) return false;
        index = (index + 1U) % 8U;
        const uint32_t entry = base + 24U + index * 16U;
        const uint32_t previous = base + 24U + ((index + 7U) % 8U) * 16U;
        uint32_t previousButtons = 0;
        if (!memory.Read32(previous, &previousButtons)) return false;
        if (!memory.WriteHost<uint64_t>(base, mSystemTicks) ||
            !memory.WriteHost<uint64_t>(base + 8U, mSystemTicks == 0 ? 1U : mSystemTicks - 1U) ||
            !memory.WriteHost<uint32_t>(entry, buttons) ||
            !memory.WriteHost<uint32_t>(entry + 4U, buttons & ~previousButtons) ||
            !memory.WriteHost<uint32_t>(entry + 8U, previousButtons & ~buttons) ||
            !memory.WriteHost<uint16_t>(entry + 12U, static_cast<uint16_t>(x)) ||
            !memory.WriteHost<uint16_t>(entry + 14U, static_cast<uint16_t>(y)) ||
            !memory.WriteHost<uint32_t>(base + 16U, index)) return false;
    }
    return true;
}
