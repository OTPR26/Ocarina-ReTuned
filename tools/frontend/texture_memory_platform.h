// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <limits>
#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#include <mach/mach.h>
#include <os/proc.h>
#include <sys/sysctl.h>
#endif
#elif defined(__ANDROID__)
#include <fstream>
#include <string>
#include <sys/sysinfo.h>
#include <unistd.h>
#endif

namespace RetunedFrontend {
inline constexpr uint64_t MiB = 1024ULL * 1024;
inline constexpr uint64_t GiB = 1024ULL * MiB;
struct TextureBudgets { uint64_t Decoded, Uploaded; };

inline TextureBudgets SelectMobileTextureBudgets(uint64_t physical, uint64_t processAllowance) {
    // Textures share memory with the title, render targets, shaders and OS.
    const uint64_t physicalShare = physical ? physical / 2 : 2 * GiB;
    const uint64_t usable = std::min(physicalShare,
                                    processAllowance ? processAllowance : physicalShare);
    if (usable < 3 * GiB / 2) return {96 * MiB, 128 * MiB};
    if (usable < 2 * GiB) return {96 * MiB, 192 * MiB};
    if (usable < 3 * GiB) return {128 * MiB, 256 * MiB};
    if (usable < 5 * GiB) return {192 * MiB, 384 * MiB};
    return {256 * MiB, 512 * MiB};
}
inline uint64_t TextureDecodeLimit(uint64_t decodedBudget, bool interfaceTexture) {
    return interfaceTexture ? decodedBudget : decodedBudget - 64 * MiB;
}
inline constexpr bool LimitTextureMemory() {
#if (defined(__APPLE__) && TARGET_OS_IPHONE) || defined(__ANDROID__)
    return true;
#else
    return false;
#endif
}
inline constexpr bool FixedTelevisionBudget() {
#if defined(__APPLE__) && TARGET_OS_TV
    return true;
#else
    return false;
#endif
}
struct TextureMemorySnapshot {
    uint64_t Physical = 0, Allowance = 0, Process = 0;
    uint64_t Available = std::numeric_limits<uint64_t>::max();
};
inline TextureMemorySnapshot ReadTextureMemorySnapshot() {
    TextureMemorySnapshot result;
#if defined(__APPLE__) && TARGET_OS_IPHONE
    size_t length = sizeof(result.Physical);
    if (sysctlbyname("hw.memsize", &result.Physical, &length, nullptr, 0) != 0) result.Physical = 0;
    result.Available = os_proc_available_memory();
    task_vm_info_data_t info{};
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&info), &count) == KERN_SUCCESS)
        result.Process = info.phys_footprint;
    result.Allowance = result.Process + result.Available;
#elif defined(__ANDROID__)
    struct sysinfo info{};
    if (sysinfo(&info) == 0) result.Physical = uint64_t(info.totalram) * info.mem_unit;
    std::ifstream memory("/proc/meminfo");
    std::string key, rest;
    uint64_t value;
    while (memory >> key >> value) {
        if (key == "MemAvailable:") { result.Available = value * 1024; break; }
        std::getline(memory, rest);
    }
    std::ifstream process("/proc/self/statm");
    uint64_t pages = 0, resident = 0;
    const auto pageSize = sysconf(_SC_PAGESIZE);
    if (pageSize > 0 && process >> pages >> resident) result.Process = resident * uint64_t(pageSize);
#endif
    return result;
}
struct TextureBudgetState {
    std::atomic<uint64_t> Decoded{128 * MiB}, Uploaded{256 * MiB};
    std::atomic<uint64_t> Available{std::numeric_limits<uint64_t>::max()};
    TextureBudgetState() {
        const auto memory = ReadTextureMemorySnapshot();
        Available.store(memory.Available);
        if (LimitTextureMemory() && !FixedTelevisionBudget()) {
            const auto budget = SelectMobileTextureBudgets(memory.Physical, memory.Allowance);
            Decoded.store(budget.Decoded);
            Uploaded.store(budget.Uploaded);
        }
    }
};
inline TextureBudgetState& TextureBudgetConfiguration() {
    static TextureBudgetState state;
    return state;
}
inline uint64_t DecodedTextureBudget() { return TextureBudgetConfiguration().Decoded.load(); }
inline uint64_t UploadedTextureBudget() { return TextureBudgetConfiguration().Uploaded.load(); }
inline void RefreshTextureMemoryBudget(uint64_t frame) {
    if (!LimitTextureMemory() || frame % 120) return;
    const auto memory = ReadTextureMemorySnapshot();
    auto& state = TextureBudgetConfiguration();
    state.Available.store(memory.Available);
    if (FixedTelevisionBudget()) return;
    const uint64_t threshold = std::clamp(memory.Physical / 16, 192 * MiB, 512 * MiB);
    if (memory.Available < threshold) {
        // Shrink once under pressure; grow again only on the next app launch.
        state.Decoded.store(std::min(state.Decoded.load(), 96 * MiB));
        state.Uploaded.store(std::min(state.Uploaded.load(), 192 * MiB));
    }
}
inline bool HasTextureAllocationHeadroom(uint64_t requested) {
    if (!LimitTextureMemory() || FixedTelevisionBudget()) return true;
    uint64_t available = TextureBudgetConfiguration().Available.load();
#if defined(__APPLE__) && TARGET_OS_IPHONE
    // The per-process limit can change at any time; query it for each upload.
    available = os_proc_available_memory();
#endif
    return available >= 128 * MiB && requested <= available - 128 * MiB;
}
}
