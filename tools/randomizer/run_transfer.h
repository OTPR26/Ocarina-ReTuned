#pragma once
#include "run_catalog.h"

namespace RetunedRandomizer {
// Call while the selected run is stopped. Bundles contain seed rules and paired
// saves, never game images, native modules, settings, or absolute paths.
struct RunBundle {
    std::string seed, runtime;
    std::vector<RunSave> saves;
    Bytes system;
};
RunBundle ReadRunBundle(const std::string& bundle);
std::string ExportRun(const std::filesystem::path& appData, unsigned slot);
RunSlot ImportRun(const std::filesystem::path& appData, unsigned emptySlot,
                  const std::string& bundle, const std::string& availableRuntime,
                  bool allowDevelopmentSeed = false);
}
