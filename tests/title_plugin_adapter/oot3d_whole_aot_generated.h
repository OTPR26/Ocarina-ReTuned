#pragma once
// ABI-only fixture for compiling the real adapter; no translated game code.
#include "triaevum_title_whole_aot_abi.h"
#include <span>
#include <type_traits>
namespace Oot3dNativeGame {
std::span<const uint32_t> Oot3dWholeAotEntryPoints() noexcept;
extern std::remove_pointer_t<Oot3dWholeAotExecuteFunctionV2> ExecuteOot3dWholeAotFunction;
}
