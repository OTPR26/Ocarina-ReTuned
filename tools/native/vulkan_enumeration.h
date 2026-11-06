// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace RetunedVulkan {
// Vulkan enumeration can legitimately return VK_INCOMPLETE between count and fill.
// Requery the count; never publish a truncated list or retry a broken driver forever.
template<class T, class Query>
std::vector<T> Enumerate(const char* operation, Query query) {
    constexpr int success = 0, incomplete = 5;
    auto fail = [operation](int result) {
        throw std::runtime_error(std::string(operation) + " failed with VkResult " + std::to_string(result));
    };
    for (unsigned attempt = 0; attempt < 8; ++attempt) {
        uint32_t count = 0;
        int result = static_cast<int>(query(&count, nullptr));
        if (result == incomplete) continue;
        if (result != success) fail(result);
        if (count == 0) return {};
        std::vector<T> values(count);
        result = static_cast<int>(query(&count, values.data()));
        if (result == incomplete) continue;
        if (result != success) fail(result);
        if (count > values.size()) continue;
        values.resize(count);
        return values;
    }
    fail(incomplete);
    return {};
}
}
