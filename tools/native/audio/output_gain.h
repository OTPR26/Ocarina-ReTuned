// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <span>
namespace Retuned {
inline std::atomic<float> OutputVolume{1.f};
inline std::atomic<bool> OutputMuted{false};
inline float ValidVolume(float value) { return std::isfinite(value)?std::clamp(value,0.f,1.f):1.f; }
inline void ApplyOutputGain(std::span<int16_t> samples,float volume,bool muted) {
 const float gain=muted?0.f:ValidVolume(volume);
 if(gain==1.f)return;
 for(auto& sample:samples)sample=static_cast<int16_t>(static_cast<float>(sample)*gain);
}
}
