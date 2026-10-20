    if (RetunedFrontend::LimitTextureMemory()) {
        RetunedFrontend::RefreshTextureMemoryBudget(mFrameCounter);
        const auto cost = [](const auto& entry) -> uint64_t {
            const auto& texture = entry.second;
            return texture.CustomReplacementApplied ? uint64_t(texture.Width) * texture.Height * 4 : 0;
        };
        // Pressure evicts least-recently-used replacements before new draws.
        // Retirement waits for this frame slot's GPU fence before destruction.
        const uint64_t interfaceBytes = RetunedFrontend::CacheBytes(mNativePicaTextures, [&](const auto& entry) {
            return RetunedFrontend::IsInterfaceTexture(entry.second.CustomReplacementHash) ? cost(entry) : 0;
        });
        const uint64_t target = mRetunedTexturePressure ?
            std::min(RetunedFrontend::UploadedTextureBudget(), interfaceBytes +
                (RetunedFrontend::UploadedTextureBudget() - RetunedFrontend::InterfaceTextureReserve) * 3 / 4) :
            RetunedFrontend::UploadedTextureBudget();
        const auto bytes = RetunedFrontend::TrimTextureCache(mNativePicaTextures, target, cost,
            [](const auto& entry) { return entry.second.RetunedLastUsedFrame; },
            [&](const auto& entry) {
                return entry.second.CustomReplacementApplied &&
                    !RetunedFrontend::IsInterfaceTexture(entry.second.CustomReplacementHash) &&
                    entry.second.RetunedLastUsedFrame < mFrameCounter;
            },
            [&](auto& entry) { RetireNativePicaTexture(entry.second); });
        mRetunedTexturePressure = false;
        RetunedFrontend::ReportTextureMemory(mFrameCounter, bytes, mNativePicaTextures.size());
    }
