#pragma once
#define VK_USE_PLATFORM_ANDROID_KHR
#include <vulkan/vulkan.h>

void* RetunedVulkanSymbol(const char* name);
