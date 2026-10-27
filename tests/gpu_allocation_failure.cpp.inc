#include <vulkan/vulkan.h>
#include <algorithm>
#include <bit>
#include <cstdint>
#include <cstdio>
#include <stdexcept>

static int failure, buffers, memories, mappings, creates;
static void Require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
extern "C" {
VKAPI_ATTR VkResult VKAPI_CALL vkCreateBuffer(VkDevice, const VkBufferCreateInfo*, const VkAllocationCallbacks*, VkBuffer* out) {
    ++creates;
    if (failure == 1) return VK_ERROR_OUT_OF_DEVICE_MEMORY;
    *out = reinterpret_cast<VkBuffer>(uintptr_t(16)); ++buffers; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL vkDestroyBuffer(VkDevice, VkBuffer, const VkAllocationCallbacks*) { --buffers; }
VKAPI_ATTR void VKAPI_CALL vkGetBufferMemoryRequirements(VkDevice, VkBuffer, VkMemoryRequirements* out) {
    *out = {}; out->size = 8192; out->alignment = 16; out->memoryTypeBits = 1;
}
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceMemoryProperties(VkPhysicalDevice, VkPhysicalDeviceMemoryProperties* out) {
    *out = {}; out->memoryTypeCount = failure == 5 ? 0 : 1;
    out->memoryTypes[0].propertyFlags = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT |
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
}
VKAPI_ATTR VkResult VKAPI_CALL vkAllocateMemory(VkDevice, const VkMemoryAllocateInfo*, const VkAllocationCallbacks*, VkDeviceMemory* out) {
    if (failure == 2) return VK_ERROR_OUT_OF_DEVICE_MEMORY;
    *out = reinterpret_cast<VkDeviceMemory>(uintptr_t(32)); ++memories; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL vkFreeMemory(VkDevice, VkDeviceMemory, const VkAllocationCallbacks*) { --memories; }
VKAPI_ATTR VkResult VKAPI_CALL vkBindBufferMemory(VkDevice, VkBuffer, VkDeviceMemory, VkDeviceSize) {
    return failure == 3 ? VK_ERROR_OUT_OF_DEVICE_MEMORY : VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL vkMapMemory(VkDevice, VkDeviceMemory, VkDeviceSize, VkDeviceSize, VkMemoryMapFlags, void** out) {
    if (failure == 4) return VK_ERROR_MEMORY_MAP_FAILED;
    *out = reinterpret_cast<void*>(uintptr_t(48)); ++mappings; return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL vkUnmapMemory(VkDevice, VkDeviceMemory) { --mappings; }
VKAPI_ATTR VkResult VKAPI_CALL vkDeviceWaitIdle(VkDevice) { return VK_SUCCESS; }
}
static uint32_t FindMemoryType(VkPhysicalDevice, uint32_t, VkMemoryPropertyFlags) {
    if (failure == 5) throw std::runtime_error("injected memory-type failure");
    return 0;
}
static void Check(VkResult result) { if (result != VK_SUCCESS) throw std::runtime_error("injected Vulkan failure"); }

struct BufferState {
    VkBuffer Handle{}, Buffer{};
    VkDeviceMemory Memory{};
    VkDeviceSize Capacity{};
    void* Mapped{};
};
struct Probe {
    using Buffer = BufferState;
    using BufferSlot = BufferState;
    VkDevice Device{};
    VkPhysicalDevice PhysicalDevice{};
    VkPhysicalDeviceMemoryProperties Memory{};
    // ACTUAL_METHODS
};

int main() {
    try {
        Probe probe;
        BufferState buffer;
        for (int step = 1; step <= 5; ++step) {
            failure = step;
            vkGetPhysicalDeviceMemoryProperties(probe.PhysicalDevice, &probe.Memory);
            bool threw = false;
            try { /* ENSURE_BUFFER */; } catch (const std::runtime_error&) { threw = true; }
            Require(threw, "fault injection did not reach creation");
            Require(buffer.Capacity == 0 && !buffer.Handle && !buffer.Buffer && !buffer.Memory && !buffer.Mapped,
                    "failed allocation left a reusable partial buffer");
            Require(buffers == 0 && memories == 0 && mappings == 0, "failed allocation leaked resources");
            failure = 0;
            vkGetPhysicalDeviceMemoryProperties(probe.PhysicalDevice, &probe.Memory);
            const int previous = creates;
            /* ENSURE_BUFFER */;
            Require(creates == previous + 1 && buffer.Mapped && buffer.Memory, "retry reused a failed allocation");
            /* ENSURE_BUFFER */;
            Require(creates == previous + 1, "valid allocation was not reused");
            /* DESTROY_BUFFER */;
            Require(buffers == 0 && memories == 0 && mappings == 0, "successful allocation leaked resources");
        }
        std::puts("PASS: five failure points, cleanup, retry, and valid reuse");
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what()); return 1;
    }
}
