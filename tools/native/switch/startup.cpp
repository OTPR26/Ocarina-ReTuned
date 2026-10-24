// SPDX-License-Identifier: GPL-2.0-or-later
#include <switch.h>
#include <cstdio>
#include <cstdint>

// Capture startup failures even if they occur in C++ static initializers,
// before main's exception handler can report them. No game content is logged.
extern "C" void userAppInit() {
    std::freopen("sdmc:/switch/oot3dre/runtime.log", "w", stdout);
    std::freopen("sdmc:/switch/oot3dre/runtime-error.log", "w", stderr);
    std::setbuf(stdout, nullptr);
    std::setbuf(stderr, nullptr);
    uint64_t available = 0, used = 0;
    const auto a = svcGetInfo(&available, InfoType_TotalMemorySize, CUR_PROCESS_HANDLE, 0);
    const auto b = svcGetInfo(&used, InfoType_UsedMemorySize, CUR_PROCESS_HANDLE, 0);
    std::printf("Switch services initialized; memory results=%u,%u total=%llu used=%llu\n",
        a, b, static_cast<unsigned long long>(available), static_cast<unsigned long long>(used));
}

extern "C" void userAppExit() {
    std::puts("Switch application exited");
}

extern "C" [[noreturn]] void __real_exit(int);
extern "C" [[noreturn]] void __wrap_exit(int status) {
    std::fprintf(stderr, "Switch exit status=%d caller=%p\n", status, __builtin_return_address(0));
    __real_exit(status);
}

extern "C" int __real_main(int, char**);
extern "C" int __wrap_main(int argc, char** argv) {
    try { throw 42; } catch (int value) { std::printf("Switch exception self-check=%d\n", value); }
    const int status = __real_main(argc, argv);
    std::fprintf(stderr, "Switch main returned status=%d\n", status);
    return status;
}

extern "C" void _start();
extern "C" [[noreturn]] void __real_abort();
extern "C" [[noreturn]] void __wrap_abort() {
    std::printf("Switch abort caller=%p offset=%llx\n", __builtin_return_address(0),
        static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)) - reinterpret_cast<uintptr_t>(&_start)));
    __real_abort();
}

#include <typeinfo>
#include <system_error>
#include <cstring>
extern "C" [[noreturn]] void __real___cxa_throw(void*, void*, void (*)(void*));
extern "C" [[noreturn]] void __wrap___cxa_throw(void* object, void* type, void (*destroy)(void*)) {
    std::printf("Switch C++ throw type=%s caller_offset=%llx\n",
        static_cast<const std::type_info*>(type)->name(),
        static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(__builtin_return_address(0)) - reinterpret_cast<uintptr_t>(&_start)));
    if (std::strcmp(static_cast<const std::type_info*>(type)->name(), "St12system_error") == 0) {
        const auto* error = static_cast<const std::system_error*>(object);
        std::printf("Switch system error code=%d message=%s\n", error->code().value(), error->what());
    }
    __real___cxa_throw(object, type, destroy);
}
