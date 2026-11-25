#pragma once
#if defined(__ANDROID__)
#include "run_launcher.h"
#include <SDL_system.h>
#include <jni.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <fstream>
#include <random>
#include <thread>
#include <cerrno>
#include <signal.h>

namespace RetunedRandomizer {
inline bool StartAndroidPreparation(const std::string& id) {
    auto* env = static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());
    if (!env || env->PushLocalFrame(4) != 0) return false;
    bool started = false;
    auto activity = static_cast<jobject>(SDL_AndroidGetActivity());
    if (activity && !env->ExceptionCheck()) {
        auto type = env->GetObjectClass(activity);
        auto method = type ? env->GetMethodID(type, "retunedPrepareRandomizer", "(Ljava/lang/String;)Z") : nullptr;
        if (method && !env->ExceptionCheck()) {
            auto value = env->NewStringUTF(id.c_str());
            if (value) started = env->CallBooleanMethod(activity, method, value) == JNI_TRUE;
        }
    }
    if (env->ExceptionCheck()) { env->ExceptionClear(); started = false; }
    env->PopLocalFrame(nullptr);
    return started;
}

inline PreparedRun PrepareAndroidRun(const std::filesystem::path& root, const std::string& seed,
                                     const RunLauncher::Progress& progress) {
    namespace fs = std::filesystem;
    using namespace std::chrono_literals;
    using Clock = std::chrono::steady_clock;
    std::random_device random;
    std::string id;
    for (int i = 0; i < 32; ++i) id += "0123456789abcdef"[random() & 15];
    const auto job = root / "jobs" / id;
    fs::create_directories(job.parent_path());
    if (!fs::create_directory(job)) throw std::runtime_error("Could not create a randomizer preparation request");
    bool started = false;
    bool finished = false;
    try {
        std::ofstream output(job / "seed.json", std::ios::binary);
        output.exceptions(std::ios::badbit | std::ios::failbit);
        output << seed;
        output.close();
        progress("Starting Android randomizer preparation…");
        started = StartAndroidPreparation(id);
        if (!started) throw std::runtime_error("Could not start Android randomizer preparation");
        const auto start = Clock::now();
        std::string message = "Waiting for Android preparation…";
        for (;;) {
            const auto status = job / "status.json";
            if (fs::exists(status)) {
                std::ifstream input(status);
                // The service commits status with AtomicFile. Retry if a read
                // overlaps the short interval between replacements.
                const auto state = nlohmann::json::parse(input, nullptr, false);
                if (!state.is_discarded()) {
                    const auto stage = state.at("stage").get<std::string>();
                    message = state.at("message").get<std::string>();
                    finished = stage == "complete" || stage == "error" || stage == "cancelled";
                    if (stage == "complete") {
                        progress(message);
                        const auto result = nlohmann::json::parse(std::ifstream(job / "result.json"));
                        PreparedRun prepared{result.at("manifest").get<std::string>(),
                                             result.at("module").get<std::string>()};
                        std::error_code ignored;
                        fs::remove_all(job, ignored);
                        return prepared;
                    }
                    if (finished) throw std::runtime_error(message);
                    const int pid = state.value("worker_pid", 0);
                    if (pid > 0 && kill(pid, 0) == -1 && errno == ESRCH) {
                        finished = true;
                        throw std::runtime_error("Android preparation stopped before finishing");
                    }
                }
            } else if (Clock::now() - start > 30s) {
                throw std::runtime_error("Android preparation did not start");
            }
            if (Clock::now() - start > 6h) throw std::runtime_error("Android preparation timed out");
            progress(message);
            std::this_thread::sleep_for(200ms);
        }
    } catch (...) {
        if (!started || finished) {
            std::error_code ignored;
            fs::remove_all(job, ignored);
        } else {
            // The isolated worker owns the request until it finishes.
            std::ofstream cancel(job / "cancel");
        }
        throw;
    }
}
}
#endif
