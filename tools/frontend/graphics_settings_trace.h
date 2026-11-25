#pragma once

#if defined(__ANDROID__)
#include <atomic>
#include <chrono>
#include <cstdio>
#if __has_include(<android/log.h>)
#include <android/log.h>
#endif
#endif

namespace RetunedFrontend {
// Only settings transitions are traced; no paths or user data are recorded.
class GraphicsSettingsTrace {
public:
    explicit GraphicsSettingsTrace(const char* operation) {
#if defined(__ANDROID__)
        operation_ = operation;
        id_ = ++sequence_;
        started_ = std::chrono::steady_clock::now();
        Mark("begin");
#endif
    }
    void Mark(const char* phase) const {
#if defined(__ANDROID__)
        const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - started_).count();
        std::fprintf(stderr, "[graphics-settings] id=%u operation=%s phase=%s elapsed_ms=%lld\n",
                     id_, operation_, phase, static_cast<long long>(elapsed));
        std::fflush(stderr);
#if __has_include(<android/log.h>)
        __android_log_print(ANDROID_LOG_INFO, "ReTunedGraphics",
                            "id=%u operation=%s phase=%s elapsed_ms=%lld",
                            id_, operation_, phase, static_cast<long long>(elapsed));
#endif
#endif
    }
    ~GraphicsSettingsTrace() { Mark("end"); }
    GraphicsSettingsTrace(const GraphicsSettingsTrace&) = delete;
    GraphicsSettingsTrace& operator=(const GraphicsSettingsTrace&) = delete;
private:
#if defined(__ANDROID__)
    inline static std::atomic<unsigned> sequence_{0};
    const char* operation_;
    unsigned id_;
    std::chrono::steady_clock::time_point started_;
#endif
};
}
