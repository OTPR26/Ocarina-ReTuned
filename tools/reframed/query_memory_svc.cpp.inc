    case 0x02: {
        event.Name = "QueryMemory";
        event.Detail = state.r[2];
        const auto info = memory.QueryRegion(state.r[2]);
        state.r[0] = kResultSuccess;
        state.r[1] = info.BaseAddress;
        state.r[2] = info.Size;
        state.r[3] = info.Permissions;
        state.r[4] = info.State;
        state.r[5] = 0U;
        event.Handled = true;
        mSvcEvents.push_back(std::move(event));
        return {NativeA32HostAction::Resume};
    }
