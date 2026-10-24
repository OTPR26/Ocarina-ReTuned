// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <algorithm>
#include <mutex>
#include <vector>
#include "texture_memory_platform.h"

namespace RetunedFrontend {
inline std::atomic<uint64_t> DecodedTextureBytes{0};
inline constexpr uint64_t InterfaceTextureReserve = 64ULL * 1024 * 1024;
inline std::mutex InterfaceTextureMutex;
inline std::vector<uint64_t> InterfaceTextureHashes;
template<class Aliases>
void PublishInterfaceTextureHashes(const Aliases& aliases) {
    std::vector<uint64_t> hashes;
    for (const auto& alias : aliases) if (alias.Native) hashes.push_back(alias.Native);
    std::scoped_lock lock(InterfaceTextureMutex);
    InterfaceTextureHashes = std::move(hashes);
}
inline bool IsInterfaceTexture(uint64_t hash) {
    std::scoped_lock lock(InterfaceTextureMutex);
    return std::find(InterfaceTextureHashes.begin(), InterfaceTextureHashes.end(), hash) != InterfaceTextureHashes.end();
}

template<class Map, class Cost>
uint64_t CacheBytes(const Map& cache, Cost cost) {
    uint64_t bytes = 0;
    for (const auto& entry : cache) bytes += cost(entry);
    return bytes;
}

// Removal transfers GPU ownership to the renderer's deferred-retirement queue.
// A protected entry can remain over budget until its current consumer finishes.
template<class Map, class Cost, class Age, class Eligible, class Retire>
uint64_t TrimTextureCache(Map& cache, uint64_t budget, Cost cost, Age age,
                          Eligible eligible, Retire retire) {
    uint64_t bytes = CacheBytes(cache, cost);
    while (bytes > budget) {
        auto oldest = cache.end();
        for (auto it = cache.begin(); it != cache.end(); ++it) {
            if (!eligible(*it)) continue;
            if (oldest == cache.end() || age(*it) < age(*oldest)) oldest = it;
        }
        if (oldest == cache.end()) break;
        bytes -= cost(*oldest);
        retire(*oldest);
        cache.erase(oldest);
    }
    return bytes;
}

inline bool FitsTextureBudget(uint64_t used, uint64_t requested, uint64_t budget) {
    return requested <= budget && used <= budget - requested;
}

template<class Texture>
uint64_t ReplacementTextureBytes(const Texture& texture) {
    return texture.CustomReplacementApplied ? uint64_t(texture.Width) * texture.Height * 4 : 0;
}
template<class Map, class Frames>
uint64_t UploadedTextureBytes(const Map& cache, const Frames& frames) {
    uint64_t bytes = CacheBytes(cache, [](const auto& entry) { return ReplacementTextureBytes(entry.second); });
    for (const auto& frame : frames)
        for (const auto& texture : frame.RetiredTextures) bytes += ReplacementTextureBytes(texture);
    return bytes;
}
template<class Map, class Frames>
bool FitsReplacementBudget(const Map& cache, const Frames& frames,
                           uint64_t requested, uint64_t hash) {
    if (!HasTextureAllocationHeadroom(requested) ||
        !FitsTextureBudget(UploadedTextureBytes(cache, frames), requested, UploadedTextureBudget())) return false;
    if (IsInterfaceTexture(hash)) return true;
    const auto sceneBytes = [](const auto& texture) -> uint64_t {
        return IsInterfaceTexture(texture.CustomReplacementHash) ? 0 : ReplacementTextureBytes(texture);
    };
    uint64_t bytes = CacheBytes(cache, [&](const auto& entry) { return sceneBytes(entry.second); });
    for (const auto& frame : frames)
        for (const auto& texture : frame.RetiredTextures) bytes += sceneBytes(texture);
    return FitsTextureBudget(bytes, requested, UploadedTextureBudget() - InterfaceTextureReserve);
}

inline void ReportTextureMemory(uint64_t frame, uint64_t gpuBytes, size_t count) {
#if defined(__APPLE__) || defined(__ANDROID__)
    if (frame % 120 != 0) return;
    const auto memory = ReadTextureMemorySnapshot();
        std::fprintf(stderr, "RETUNED_TEXTURE_MEMORY decoded=%llu gpu=%llu textures=%zu footprint=%llu available=%llu decoded_budget=%llu gpu_budget=%llu adaptive=%d\n",
            static_cast<unsigned long long>(DecodedTextureBytes.load()),
            static_cast<unsigned long long>(gpuBytes), count,
            static_cast<unsigned long long>(memory.Process),
            static_cast<unsigned long long>(memory.Available),
            static_cast<unsigned long long>(DecodedTextureBudget()),
            static_cast<unsigned long long>(UploadedTextureBudget()), int(LimitTextureMemory()));
    std::fflush(stderr);
#else
    (void)frame; (void)gpuBytes; (void)count;
#endif
}
}
