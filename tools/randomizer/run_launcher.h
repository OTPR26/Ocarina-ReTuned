#pragma once
#include "run_catalog.h"
#include <atomic>
#include <functional>
#include <future>
#include <optional>
#include <mutex>

namespace RetunedRandomizer {
struct PreparedRun {
    std::filesystem::path manifest, module;
};
// Reuse an installed seed-independent module. This adapter needs no Python,
// compiler, or subprocess and can be used by each platform's startup host.
PreparedRun BindSeedToRuntime(const PreparedRun& installed, const std::string& seed,
                             const std::filesystem::path& artifacts,
                             bool development = false);
// Candidates come from the platform's installed/retained runtime inventory,
// never from a save document. Every candidate is validated against the run.
PreparedRun ResolveRunRuntime(const std::filesystem::path& manifest,
                             const std::vector<std::filesystem::path>& modules,
                             const std::string& runtimeHash, const std::string& seedHash,
                             bool development = false);
std::vector<PreparedRun> RetainedRuntimeInventory(const std::filesystem::path& store);
PreparedRun RestoreRunRuntime(const RunSlot& run, const std::vector<PreparedRun>& inventory,
                             const std::filesystem::path& artifacts, bool development = false);
struct LaunchRequest {
    PreparedRun prepared;
    RunSlot run;
    unsigned menuSlot = 0;
    unsigned guestSlot = 0;
};
// Preparation runs away from the UI. The host consumes the request on its own
// thread and starts a fresh guest process; this class never switches live memory.
class RunLauncher {
public:
    using Progress = std::function<void(const std::string&)>;
    using Generate = std::function<std::string(const std::string&, const Progress&)>;
    using Prepare = std::function<PreparedRun(const std::string&, const Progress&)>;
    using Resolve = std::function<PreparedRun(unsigned)>;
    RunLauncher(const std::filesystem::path& appData, Generate generate,
                Prepare prepare, Resolve resolve, bool development = false);
    ~RunLauncher();
    RunLauncher(const RunLauncher&) = delete;
    RunLauncher& operator=(const RunLauncher&) = delete;
    bool Create(unsigned slot, const std::string& seed);
    bool Continue(unsigned slot);
    // Platforms deliver document bytes after their picker returns. The host must
    // allow these operations only before starting a guest.
    bool Import(unsigned emptySlot, const std::string& bundle);
    std::string Export(unsigned slot) const;
    void Cancel();
    bool Busy() const;
    std::string Status() const;
    std::array<RunSlot, 3> Slots() const;
    std::optional<LaunchRequest> Poll();
private:
    bool Begin(unsigned slot, std::optional<std::string> seed);
    void Report(const std::string& text);
    std::filesystem::path appData_;
    RunCatalog catalog_;
    Generate generate_;
    Prepare prepare_;
    Resolve resolve_;
    bool development_;
    std::atomic<bool> cancel_{false};
    mutable std::mutex mutex_;
    std::string status_;
    std::future<LaunchRequest> pending_;
};
}
