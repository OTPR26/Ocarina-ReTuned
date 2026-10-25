#include "touch_input_api.h"
#include "fast/oot3d/retuned_touch_overlay.h"
extern "C" void RetunedTouchSetHudAnchor(int slot,float x,float y){RetunedFrontend::SetTouchHudAnchor(slot,x,y);}
extern "C" void RetunedTouchSetHudDisplay(float width,float height){
 RetunedFrontend::SetTouchHudDisplay(width,height);
}
extern "C" void RetunedTouchSetButton(int button,int pressed) {
 using namespace RetunedFrontend;
 TouchAction action;
 switch(button) {
 case 0:action=TouchAction::A;break;case 1:action=TouchAction::B;break;
 case 2:action=TouchAction::X;break;case 3:action=TouchAction::Y;break;
 case 4:action=TouchAction::Settings;break;case 6:action=TouchAction::Inventory;break;
 case 9:action=TouchAction::Target;break;case 10:action=TouchAction::Shield;break;
 case 11:action=TouchAction::Up;break;case 12:action=TouchAction::Down;break;
 case 13:action=TouchAction::Left;break;case 14:action=TouchAction::Right;break;
 default:return;
 }
 std::lock_guard lock(TouchMutex);NativeTouch.SourceButton(button,action,pressed!=0);
}
extern "C" void RetunedTouchSetAxis(int axis,int value) {
 using namespace RetunedFrontend;
 std::lock_guard lock(TouchMutex);
 const float v=std::clamp(value/32767.f,-1.f,1.f);
 if(axis==0)NativeTouch.MoveX=v;if(axis==1)NativeTouch.MoveY=-v;
 if(axis==2)NativeTouch.LookX=v;if(axis==3)NativeTouch.LookY=-v;
 if(axis==4||axis==5) {
  const int action=ExtraShoulderAction(TouchExtraShoulders.load(),axis==4?TouchZLAction.load():TouchZRAction.load());
  if(action>=0)NativeTouch.SourceButton(100+axis,static_cast<TouchAction>(action),value>0);
 }
}
extern "C" void RetunedTouchSetEnabled(int enabled) {
 using namespace RetunedFrontend;
 TouchVisibility.Show(enabled!=0);
 std::lock_guard lock(TouchMutex);NativeTouch.Reset();
}
#ifdef __ANDROID__
#include <jni.h>
#include "texture_folder_jni.h"
extern "C" JNIEXPORT jfloat JNICALL Java_org_triaevum_android_TouchOverlay_opacity(JNIEnv*,jclass){return RetunedFrontend::NativeTouchOpacity.load();}
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_button(JNIEnv*,jclass,jint button,jboolean down) {RetunedTouchSetButton(button,down);}
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_axis(JNIEnv*,jclass,jint axis,jint value) {RetunedTouchSetAxis(axis,value);}
extern "C" JNIEXPORT jint JNICALL Java_org_triaevum_android_TouchOverlay_state(JNIEnv*,jclass) {
 using namespace RetunedFrontend;
 return (NativeFrontendEnabled?1:0)|(TouchHostMenu.load()?2:0)|(TouchVisibility.ControlsVisible()?4:0)|(TouchVisibility.ButtonVisible()?512:0)|(TouchFaceLayout.load()<<3)|(TouchHostMode.load()!=0?32:0)|(TouchFloating.load()?64:0)|(TouchExtraShoulders.load()?128:0)|(TouchHudActive.load()&&TouchHudLive.load()?256:0);
}
#endif

#ifdef __ANDROID__
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_enabled(JNIEnv*,jclass,jboolean enabled){RetunedTouchSetEnabled(enabled);}
extern "C" JNIEXPORT jfloat JNICALL Java_org_triaevum_android_TouchOverlay_size(JNIEnv*,jclass){return RetunedFrontend::TouchSize.load();}
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_displayMetrics(JNIEnv*,jclass,jfloat density,jfloat height){RetunedFrontend::InstallAndroidTextureFolder();RetunedFrontend::AndroidDisplayDensity=density;RetunedFrontend::AndroidDisplayHeight=height;}
#endif

#ifdef __ANDROID__
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_hudAnchor(JNIEnv*,jclass,jint slot,jfloat x,jfloat y){RetunedTouchSetHudAnchor(slot,x,y);}
extern "C" JNIEXPORT void JNICALL Java_org_triaevum_android_TouchOverlay_hudDisplay(JNIEnv*,jclass,jfloat width,jfloat height){RetunedTouchSetHudDisplay(width,height);}
#endif
