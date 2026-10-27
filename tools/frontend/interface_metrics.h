// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
extern "C" float RetunedAppleScreenScale();
#endif
#endif
#include <atomic>
struct ImFont;
namespace RetunedFrontend {
inline ImFont* InterfaceBoldFont=nullptr;
inline ImFont* InterfaceHeadingFont=nullptr;
inline ImFont* InterfaceHeadingBoldFont=nullptr;
inline ImFont* InterfaceDisplayFont=nullptr;
inline constexpr float InterfaceBodySize=15.f;
inline constexpr float InterfaceHeadingSize=20.f;
inline constexpr float StartupBodySize=20.f;
inline constexpr float StartupButtonSize=32.f;
inline std::atomic<float> AndroidDisplayDensity{1.f},AndroidDisplayHeight{0.f};
inline float MenuSize=1.f;
inline constexpr bool TelevisionPlatform() {
#if defined(__APPLE__) && TARGET_OS_TV
 return true;
#else
 return false;
#endif
}
inline constexpr bool MobileSettingsPlatform() {
#if defined(__IOS__) || defined(__ANDROID__)
 return true;
#else
 return false;
#endif
}
inline float MenuScale(float height) {
#ifdef __ANDROID__
 const float displayHeight=AndroidDisplayHeight.load();
 return MenuSize*(displayHeight>0 ? AndroidDisplayDensity.load()*height/displayHeight : 1.f);
#elif defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
 return MenuSize;
#else
 return MenuSize;
#endif
}

inline float InterfacePixelRatio=1.f;
inline constexpr float InterfaceAtlasSize=64.f;
inline float InterfaceFontPixels() { return InterfaceAtlasSize*InterfacePixelRatio; }
inline float InterfaceFontScale(float scale=1.f,float size=InterfaceBodySize) { return size*scale/InterfaceFontPixels(); }
inline void SetInterfacePixelRatio(float logicalWidth,float pixelWidth) {
 InterfacePixelRatio=logicalWidth>0 ? std::clamp(pixelWidth/logicalWidth,1.f,4.f) : 1.f;
#ifdef __ANDROID__
 InterfacePixelRatio=std::max(InterfacePixelRatio,std::clamp(AndroidDisplayDensity.load(),1.f,4.f));
#endif
#if defined(__APPLE__) && TARGET_OS_IPHONE
 // The font atlas is prepared before Vulkan has created its Metal view.
 InterfacePixelRatio=std::max(InterfacePixelRatio,RetunedAppleScreenScale());
#endif
}
}
