#pragma once
#include <functional>
#include <string>
namespace RetunedRandomizer {
// Calls are serialized: the pinned generator has global mutable state.
// Throw from progress to cancel before the next fill attempt.
std::string Generate(const std::string& seed, const std::function<void(unsigned)>& progress = {});
}
