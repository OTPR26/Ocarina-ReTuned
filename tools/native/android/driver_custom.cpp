#include <adrenotools/driver.h>
#include <dlfcn.h>
#include <string>

extern "C" __attribute__((visibility("default")))
void* RetunedOpenCustomDriver(const char* hooks, const char* directory, const char* library) {
    // libadrenotools concatenates the directory and filename without a separator.
    const std::string path = std::string(directory) + "/";
    return adrenotools_open_libvulkan(RTLD_NOW | RTLD_LOCAL, ADRENOTOOLS_DRIVER_CUSTOM,
        nullptr, hooks, path.c_str(), library, nullptr, nullptr);
}
