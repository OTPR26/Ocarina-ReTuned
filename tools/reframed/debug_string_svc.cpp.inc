    case 0x3D: {
        event.Name = "OutputDebugString";
        const uint32_t address = state.r[0], length = state.r[1];
        event.Detail = length;
        if (length != 0U && !memory.IsMapped(address, length)) {
            mSvcEvents.push_back(std::move(event));
            return {NativeA32HostAction::Wait};
        }
        // Keep diagnostics bounded; the console API uses a length, not a NUL terminator.
        std::vector<uint8_t> text(std::min(length, 1024U));
        if (!text.empty()) {
            if (!memory.ReadBytes(address, text)) {
                mSvcEvents.push_back(std::move(event));
                return {NativeA32HostAction::Wait};
            }
            event.Name += ":" + std::string(text.begin(), text.end());
        }
        state.r[0] = kResultSuccess;
        event.Handled = true;
        mSvcEvents.push_back(std::move(event));
        return {NativeA32HostAction::Resume};
    }
