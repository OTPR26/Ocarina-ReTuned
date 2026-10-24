// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <optional>
namespace RetunedDeko {
constexpr uint64_t TextureGpuBudget = 256ULL * 1024 * 1024;
constexpr size_t TextureRecordBudget = 2048;
constexpr uint64_t TextureUploadPerFrame = 4ULL * 1024 * 1024;
constexpr uint64_t MaxReplacementBytes = 64ULL * 1024 * 1024;
inline std::optional<size_t> NativeTextureBaseBytes(unsigned format,unsigned width,unsigned height) {
 constexpr unsigned nibbles[]={8,6,4,4,4,4,4,2,2,2,1,1,1,2};
 if(format>=14||!width||!height||width>8192||height>8192)return {};
 uint64_t w=(std::max(8u,width)+7u)&~7u,h=(std::max(8u,height)+7u)&~7u;
 return size_t((w*h*nibbles[format]+1)/2);
}
inline bool ReplacementFits(unsigned width,unsigned height,size_t bytes,
                            uint64_t resident,uint64_t uploaded) {
 if(!width||!height||width>8192||height>8192||uint64_t(width)*height*4!=bytes)return false;
 if(bytes>MaxReplacementBytes||resident>TextureGpuBudget||bytes>TextureGpuBudget-resident)return false;
 // One larger mobile atlas may upload first; don't burst many in one frame.
 return uploaded==0||(uploaded<TextureUploadPerFrame&&bytes<=TextureUploadPerFrame-uploaded);
}
}
