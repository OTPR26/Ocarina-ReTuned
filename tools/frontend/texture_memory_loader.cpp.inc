    void TrimDecodedTexturesLocked(uint64_t protectedHash) {
        if (!RetunedFrontend::LimitTextureMemory()) return;
        const auto replacementBytes = [](const auto& entry) -> uint64_t {
            return entry.second && entry.second->Rgba8 ? entry.second->Rgba8->size() : 0;
        };
        const auto materialBytes = [](const auto& entry) -> uint64_t {
            uint64_t bytes = 0;
            if (entry.second->ColorReplacement && entry.second->ColorReplacement->Rgba8)
                bytes += entry.second->ColorReplacement->Rgba8->size();
            for (const auto& texture : entry.second->Textures)
                if (texture && texture->Rgba8) bytes += texture->Rgba8->size();
            return bytes;
        };
        const auto age = [&](const auto& entry) {
            const auto it = mRetunedTextureUse.find(entry.first);
            return it == mRetunedTextureUse.end() ? 0ULL : it->second;
        };
        const auto eligible = [&](const auto& entry) {
            return entry.first != protectedHash && !RetunedFrontend::IsInterfaceTexture(entry.first);
        };
        const auto retire = [&](const auto& entry) {
            mRetunedTextureUse.erase(entry.first);
            mRetunedEvictedTextures.insert(entry.first);
        };
        mRetunedTextureUse[protectedHash] = ++mRetunedTextureClock;
        const auto materials = RetunedFrontend::TrimTextureCache(mMaterialCache,
            RetunedFrontend::DecodedTextureBudget() / 2, materialBytes, age, eligible, retire);
        const auto replacements = RetunedFrontend::TrimTextureCache(mReplacementCache,
            RetunedFrontend::DecodedTextureBudget(), replacementBytes, age, eligible, retire);
        RetunedFrontend::DecodedTextureBytes.store(materials + replacements);
    }
