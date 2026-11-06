#include "vulkan_enumeration.h"
#include <cassert>
#include <iostream>
#include <string>

int main() {
    using RetunedVulkan::Enumerate;
    int countCalls=0, fillCalls=0;
    auto grown=Enumerate<int>("vkEnumeratePhysicalDevices", [&](uint32_t* count, int* values) {
        if (!values) { *count=++countCalls; return 0; }
        if (++fillCalls==1) { values[0]=7; *count=1; return 5; }
        values[0]=7; values[1]=9; *count=2; return 0;
    });
    assert((grown==std::vector<int>{7,9}) && countCalls==2 && fillCalls==2);
    auto shrunk=Enumerate<int>("vkGetPhysicalDeviceSurfaceFormatsKHR", [](uint32_t* count, int* values) {
        if (!values) { *count=3; return 0; }
        values[0]=17; *count=1; return 0;
    });
    assert((shrunk==std::vector<int>{17}));
    int emptyCalls=0;
    assert(Enumerate<int>("empty", [&](uint32_t* count, int* values) {
        assert(!values); ++emptyCalls; *count=0; return 0;
    }).empty() && emptyCalls==1);
    int attempts=0;
    try {
        Enumerate<int>("vkEnumeratePhysicalDevices", [&](uint32_t* count, int* values) {
            if (!values) { *count=1; return 0; }
            ++attempts; return 5;
        });
        assert(false);
    } catch (const std::runtime_error& error) {
        assert(attempts==8 && std::string(error.what())=="vkEnumeratePhysicalDevices failed with VkResult 5");
    }
    for (bool failCount : {false,true}) {
        try {
            Enumerate<int>("vkEnumerateDeviceExtensionProperties", [=](uint32_t* count, int* values) {
                if (!values) { *count=1; return failCount ? -3 : 0; }
                return -4;
            });
            assert(false);
        } catch (const std::runtime_error& error) {
            assert(std::string(error.what())==std::string("vkEnumerateDeviceExtensionProperties failed with VkResult ")+(failCount ? "-3" : "-4"));
        }
    }
    int countRetries=0;
    auto recovered=Enumerate<int>("count", [&](uint32_t* count,int* values) {
        if (!values) { *count=1; return ++countRetries==1 ? 5 : 0; }
        values[0]=4; *count=1; return 0;
    });
    assert((recovered==std::vector<int>{4}) && countRetries==2);
    std::cout << "PASS: growing/shrinking lists, incomplete retries, empty results, fatal errors, and retry bounds\n";
}
