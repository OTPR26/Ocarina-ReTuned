#pragma once
#include <filesystem>
// Returns false when setup was cancelled. No effect for diagnostic/custom CLI
// invocations or an existing launch profile.
bool RetunedFirstRun(int argc, char** argv, std::filesystem::path& profile);

// Called after the running host has released its game and rendering resources.
int RetunedFinishPreparationRequest(int result);
