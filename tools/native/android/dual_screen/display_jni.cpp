// SPDX-License-Identifier: GPL-2.0-or-later
#include <vulkan/vulkan.h>
#include "android_secondary_swapchain.h"
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_RetunedDualScreen_surface(JNIEnv* env,jclass,jobject surface) {RetunedFrontend::AndroidSetLowerSurface(env,surface);}
extern "C" JNIEXPORT jboolean JNICALL Java_org_triaevum_android_RetunedDualScreen_displayWanted(JNIEnv*,jclass) {return RetunedFrontend::AndroidDualSelected.load()||RetunedFrontend::AndroidGuestDualActive.load();}
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_RetunedDualScreen_touch(JNIEnv*,jclass,jint x,jint y,jboolean pressed) {
 RetunedFrontend::AndroidLowerTouch=pressed&&x>=0&&x<320&&y>=0&&y<240?0x80000000u|(unsigned(x)<<8)|unsigned(y):0;
}
