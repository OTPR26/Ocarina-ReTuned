#include "driver_loader.h"
#include <android/log.h>
#include <dlfcn.h>
#include <jni.h>
#include <cstdlib>
#include <mutex>
#include <string>
#include <vector>
#include <cstdio>

namespace {
std::mutex loaderMutex;
void* loader = nullptr;
std::string selection;

std::string String(JNIEnv* env, jstring value) {
    if (!value) return {};
    const char* bytes = env->GetStringUTFChars(value, nullptr);
    if (!bytes) return {};
    std::string result(bytes);
    env->ReleaseStringUTFChars(value, bytes);
    return result;
}
}

extern "C" const char* RetunedInitializeVulkan(const char* hooks, const char* directory, const char* library) {
    std::lock_guard lock(loaderMutex);
    const std::string hookPath(hooks), driverPath(directory), driverName(library);
    const auto requested = driverPath + "/" + driverName;
    if (loader) return selection == requested ? "" : "Changing the graphics driver requires restarting the app.";
    if (driverPath.empty()) {
        loader = dlopen("libvulkan.so", RTLD_NOW | RTLD_LOCAL);
    } else {
        void* helper = dlopen((hookPath + "/libretuned_driver.so").c_str(), RTLD_NOW | RTLD_LOCAL);
        using Open = void* (*)(const char*, const char*, const char*);
        auto open = helper ? reinterpret_cast<Open>(dlsym(helper, "RetunedOpenCustomDriver")) : nullptr;
        if (!open) return "The custom-driver helper is unavailable. Select System driver to recover.";
        loader = open(hookPath.c_str(), driverPath.c_str(), driverName.c_str());
    }
    if (!loader) return "The selected graphics driver could not be loaded. Select System driver to recover.";
    selection = requested;
    return "";
}

extern "C" JNIEXPORT jstring JNICALL
Java_org_triaevum_android_GraphicsDriver_initialize(
    JNIEnv* env, jclass, jstring hooks, jstring directory, jstring library) {
    const auto hookPath = String(env, hooks);
    const auto driverPath = String(env, directory);
    const auto driverName = String(env, library);
    return env->NewStringUTF(RetunedInitializeVulkan(hookPath.c_str(), driverPath.c_str(), driverName.c_str()));
}

void* RetunedVulkanSymbol(const char* name) {
    std::lock_guard lock(loaderMutex);
    if (!loader) {
        __android_log_assert("driver initialized", "ReTuned", "Vulkan called before graphics driver selection");
    }
    void* function = dlsym(loader, name);
    if (!function) {
        __android_log_assert("Vulkan entry point", "ReTuned", "Missing Vulkan entry point %s", name);
    }
    return function;
}

extern "C" JNIEXPORT jlongArray JNICALL
Java_org_triaevum_android_GraphicsDriver_inspect(JNIEnv* env, jclass) {
    auto fail = [&](const char* message) -> jlongArray {
        env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), message);
        return nullptr;
    };
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.apiVersion = VK_API_VERSION_1_2;
    VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    info.pApplicationInfo = &app;
    VkInstance instance{};
    if (vkCreateInstance(&info, nullptr, &instance) != VK_SUCCESS)
        return fail("This driver cannot create a Vulkan 1.2 instance.");
    uint32_t count = 0;
    VkResult result = vkEnumeratePhysicalDevices(instance, &count, nullptr);
    if (result != VK_SUCCESS || !count || count > 32) {
        vkDestroyInstance(instance, nullptr);
        return fail("No usable Vulkan graphics device was found.");
    }
    std::vector<VkPhysicalDevice> devices(count);
    result = vkEnumeratePhysicalDevices(instance, &count, devices.data());
    jlong values[4]{};
    bool supported = false;
    if (result == VK_SUCCESS) for (uint32_t i = 0; i < count; ++i) {
        VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
        VkPhysicalDeviceProperties2 properties{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};
        properties.pNext = &driver;
        vkGetPhysicalDeviceProperties2(devices[i], &properties);
        if (properties.properties.apiVersion < VK_API_VERSION_1_2) continue;
        uint32_t queueCount = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queueCount, nullptr);
        if (!queueCount || queueCount > 256) continue;
        std::vector<VkQueueFamilyProperties> queues(queueCount);
        vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &queueCount, queues.data());
        for (uint32_t q = 0; q < queueCount; ++q) {
            if (!(queues[q].queueFlags & VK_QUEUE_GRAPHICS_BIT) || !queues[q].queueCount) continue;
            float priority = 1.f;
            VkDeviceQueueCreateInfo queue{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
            queue.queueFamilyIndex = q; queue.queueCount = 1; queue.pQueuePriorities = &priority;
            VkDeviceCreateInfo create{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
            create.queueCreateInfoCount = 1; create.pQueueCreateInfos = &queue;
            VkDevice device{};
            if (vkCreateDevice(devices[i], &create, nullptr, &device) != VK_SUCCESS) continue;
            vkDestroyDevice(device, nullptr);
            values[0] = properties.properties.apiVersion;
            values[1] = properties.properties.vendorID;
            values[2] = properties.properties.driverVersion;
            values[3] = driver.driverID;
            supported = true;
            break;
        }
        if (supported) break;
    }
    vkDestroyInstance(instance, nullptr);
    if (!supported) return fail("The selected driver does not provide a usable Vulkan 1.2 graphics device.");
    // Confirm the requested file was actually mapped, rather than a loader fallback.
    if (selection != "/") {
        bool mapped = false;
        char* resolved = realpath(selection.c_str(), nullptr);
        const std::string expected = resolved ? resolved : selection;
        free(resolved);
        FILE* maps = fopen("/proc/self/maps", "r");
        if (maps) {
            char* line = nullptr; size_t capacity = 0;
            while (getline(&line, &capacity, maps) >= 0)
                if (std::string(line).find(expected) != std::string::npos) mapped = true;
            free(line); fclose(maps);
        }
        if (!mapped) return fail("The custom driver was not activated. System driver remains available.");
    }
    auto output = env->NewLongArray(4);
    if (output) env->SetLongArrayRegion(output, 0, 4, values);
    return output;
}
