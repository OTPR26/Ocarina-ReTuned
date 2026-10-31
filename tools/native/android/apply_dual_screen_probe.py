"""Install optional Android dual-display presentation and equipment controls."""
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'frontend'),str(Path(__file__).resolve().parents[2]/'reframed')]
from apply_reframed_screen_probe import apply as presentation

def apply(root):
 root=Path(root)
 # Shared presentation staging rewrites its headers. Preserve the Android
 # additions on repeated application to this private experimental tree.
 marker=root/'runtime/three_ds_recomp/include/fast/oot3d/android_secondary_swapchain.h'
 if not marker.exists():presentation(root)
 here=Path(__file__).parent/'dual_screen';inc=root/'runtime/three_ds_recomp/include/fast/oot3d';runtime=root/'tools/oot3d/native_game_runtime'
 for src,dst in [('display_state.h','android_display_state.h'),('secondary_swapchain.h','android_secondary_swapchain.h')]: (inc/dst).write_bytes((here/src).read_bytes())
 (inc/'lower_equipment_state.h').write_bytes((here.parents[2]/'frontend/lower_equipment_state.h').read_bytes())
 (inc/'retuned_lower_equipment.h').write_bytes((here.parents[2]/'frontend/lower_equipment.h').read_bytes())
 (runtime/'retuned_shared_lower_equipment_runtime.h').write_bytes((here.parents[1]/'lower_equipment_runtime.h').read_bytes())
 (runtime/'retuned_lower_equipment_runtime.h').write_bytes((here/'equipment_runtime.h').read_bytes())
 def edit(path,before,after):
  s=path.read_text()
  if after in s:return
  if s.count(before)!=1:raise ValueError('Android dual context changed: '+str(path)+' '+before[:50])
  path.write_text(s.replace(before,after))
 probe=inc/'retuned_screen_probe.h'
 edit(probe,'#include "duo_game_display.h"','#include "duo_game_display.h"\n#include "android_display_state.h"')
 edit(probe,'inline bool ScreenProbeRequested(){return DuoProbeRequested()', 'inline bool ScreenProbeRequested(){return AndroidDualProbeRequested() || DuoProbeRequested()')
 edit(probe,'inline bool ScreenProbeEnabled(){return (DuoProbeRequested() && DuoDisplay.Available())', 'inline bool ScreenProbeEnabled(){return (AndroidDualProbeRequested() && ProbeGuestDualActive.load()) || (DuoProbeRequested() && DuoDisplay.Available())')
 old=' if(AndroidDualProbeRequested())return {{0,0,width,height},FitScreen({0,0,width,height},320.f/240.f)};'
 text=probe.read_text();text=text.replace(old,'')
 text=text.replace('auto lower=FitScreen({0,0,width,height},320.f/240.f);lower.Y=0;', 'auto lower=FitScreen({0,0,width,height},320.f/240.f);if(LowerEquipmentPanelEnabled.load())lower.Y=0;')
 probe.write_text(text)
 edit(probe,'inline GameScreenLayout ScreenProbeLayout(float width,float height) {','inline GameScreenLayout ScreenProbeLayout(float width,float height) {\n if(AndroidDualProbeRequested()){auto lower=FitScreen({0,0,width,height},320.f/240.f);if(LowerEquipmentPanelEnabled.load())lower.Y=0;return {{0,0,width,height},lower};}')
 frame=runtime/'oot3d_native_a32_window_frame.cpp'
 edit(frame,'#include "retuned_reframed_screen_probe.h"','#include "retuned_reframed_screen_probe.h"\n#ifdef __ANDROID__\n#include "retuned_lower_equipment_runtime.h"\n#endif')
 edit(frame,'  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(','''#ifdef __ANDROID__
  RetunedFrontend::UpdateLowerEquipment(process,gui->GetMenuOrMenubarVisible() || gui->GetAnyGuiWindowVisible() || RetunedFrontend::StartupVisible);
#endif
  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(''')
 bridge=runtime/'retuned_reframed_screen_probe.h'
 edit(bridge,'        // Private diagnostic control only.', '        if (AndroidDualProbeRequested()) requested = AndroidLowerAvailable.load() && AndroidDualSelected.load() ? GamePresentation::Dual : GamePresentation::Single;\n        // Private diagnostic control only.')
 edit(bridge,'        ProbeGuestDualActive = mBridge.Effective() == GamePresentation::Dual;',
      '        ProbeGuestDualActive = mBridge.Effective() == GamePresentation::Dual;\n        if(AndroidDualProbeRequested())AndroidGuestDualActive=ProbeGuestDualActive.load();')
 setup=runtime/'oot3d_native_a32_window_setup.cpp'
 edit(setup,'  context = Ship::Context::GetRawInstance();','  context = Ship::Context::GetRawInstance();\n  RetunedFrontend::LowerEquipmentPanelEnabled=context->GetConfig()->GetBool("Interface.DualEquipmentPanel",true);\n  if(RetunedFrontend::AndroidDualProbeRequested())RetunedFrontend::AndroidDualSelected=context->GetConfig()->GetBool("Interface.DualScreen",true);')
 graphics=root/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
 text=graphics.read_text()
 start=text.find('        if(RetunedFrontend::AndroidDualProbeRequested()) {\n            ImGui::SeparatorText("Display");')
 if start>=0 and 'Bottom equipment panel' not in text:
  end=text.index('        ImGui::SeparatorText("Menu");',start)
  graphics.write_text(text[:start]+text[end:])

 edit(graphics,'#include <algorithm>','#include <algorithm>\n#include "fast/oot3d/android_display_state.h"')
 from panel_staging import stage_platform_display_settings
 stage_platform_display_settings(root)
 (inc/'android_lower_resolution.h').write_bytes((here/'lower_resolution.h').read_bytes())
 resolution=inc/'render_resolution_policy.h'
 edit(resolution,'#include "fast/oot3d/graphics_settings.h"','#include "fast/oot3d/graphics_settings.h"\n#include "android_display_state.h"\n#include "android_lower_resolution.h"')
 edit(resolution,'    RenderExtent base = guestExtent;','''#ifdef __ANDROID__
    if(RetunedFrontend::AndroidDualProbeRequested() && RetunedFrontend::AndroidGuestDualActive.load()) {
        if(const auto lower=RetunedFrontend::AndroidLowerRenderExtent(guestExtent.Width,guestExtent.Height,
             RetunedFrontend::AndroidLowerWidth.load(),RetunedFrontend::AndroidLowerHeight.load()))
            return ScaleRenderExtent({lower->Width,lower->Height},internalScale);
    }
#endif
    RenderExtent base = guestExtent;''')
 targets=root/'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_pica.cpp'
 edit(targets,'    target.Height = targetExtent.Height;','''    target.Height = targetExtent.Height;
#ifdef __ANDROID__
    if(RetunedFrontend::AndroidDualProbeRequested() && RetunedFrontend::AndroidGuestDualActive.load() &&
       key.Height==320 && (key.Width==240 || key.Width==480))
        std::fprintf(stderr,"RETUNED_LOWER_RESOLUTION guest=%ux%u render=%ux%u\\n",key.Width,key.Height,target.Width,target.Height);
#endif''')
 hdr=root/'runtime/three_ds_recomp/include/fast/backends/gfx_vulkan.h'
 edit(hdr,'#include <vulkan/vulkan.h>','#include <vulkan/vulkan.h>\n#ifdef __ANDROID__\n#include "fast/oot3d/android_secondary_swapchain.h"\n#endif')
 edit(hdr,'    VkInstance mInstance = VK_NULL_HANDLE;','    VkInstance mInstance = VK_NULL_HANDLE;\n#ifdef __ANDROID__\n    RetunedFrontend::AndroidSecondarySwapchain mAndroidLower;\n#endif')
 display=root/'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_pica_display.cpp'
 edit(display,'        const bool copyBoundary = copyOutput != nullptr;', '''        const bool copyBoundary = copyOutput != nullptr;
#ifdef __ANDROID__
        const bool androidLower = !copyBoundary && RetunedFrontend::AndroidDualProbeRequested() &&
            RetunedFrontend::ProbeGuestDualActive.load() && RetunedFrontend::ProbeScanoutScreen == RetunedFrontend::GameScreen::Lower;
        const auto oldExtent=mSwapchainExtent;
        const auto oldImage=mSwapchainImages[mCurrentImage];
        const auto oldView=mSwapchainImageViews[mCurrentImage];
        const auto oldFramebuffer=mSwapchainFramebuffers[mCurrentImage];
        const auto oldTransfer=mLastPresentedNativePicaDisplayTransfer;
        const bool oldPresented=mNativePicaPresentedThisFrame;
        RetunedFrontend::AndroidOutputRestore restoreAndroid([&]{if(androidLower){
            mSwapchainExtent=oldExtent;mSwapchainImages[mCurrentImage]=oldImage;
            mSwapchainImageViews[mCurrentImage]=oldView;mSwapchainFramebuffers[mCurrentImage]=oldFramebuffer;
            mLastPresentedNativePicaDisplayTransfer=oldTransfer;mNativePicaPresentedThisFrame=oldPresented;
        }});
        if(androidLower){
            if(!mAndroidLower.Acquire(mInstance,mPhysicalDevice,mDevice,mGraphicsQueueFamily,mSwapchainFormat,mDepthFormat,mRenderPass,mCommandBuffers[mCurrentFrame],mFrameCounter))return true;
            mSwapchainExtent=mAndroidLower.Extent;mSwapchainImages[mCurrentImage]=mAndroidLower.Image();
            mSwapchainImageViews[mCurrentImage]=mAndroidLower.View();mSwapchainFramebuffers[mCurrentImage]=mAndroidLower.Framebuffer();
        }
#endif''')
 edit(display,'        const bool alphaOverlay = !copyBoundary &&','''        const bool alphaOverlay = !copyBoundary &&
#ifdef __ANDROID__
            !androidLower &&
#endif''')
 frame=display.with_name('gfx_vulkan_frame.cpp')
 edit(frame,'    mFrameActive = false;\n    mFrameSubmitted = true;','''#ifdef __ANDROID__
    if(RetunedFrontend::AndroidDualProbeRequested())mAndroidLower.Present(mGraphicsQueue);
#endif
    mFrameActive = false;
    mFrameSubmitted = true;''')
 lifecycle=display.with_name('gfx_vulkan_lifecycle.cpp')
 edit(lifecycle,'        vkDestroyDevice(mDevice, nullptr);','''#ifdef __ANDROID__
        mAndroidLower.Destroy();
#endif
        vkDestroyDevice(mDevice, nullptr);''')
 inp=runtime/'oot3d_native_a32_window_input.cpp'
 # The shared probe maps a single window. Android gets independent lower touches.
 edit(inp,'    const auto touch=RetunedFrontend::ScreenProbeTouch(window.GetWidth(),window.GetHeight(),pointer.x,pointer.y);', '''    const auto touch=RetunedFrontend::AndroidDualProbeRequested() ? std::optional<RetunedFrontend::LowerScreenTouch>{} : RetunedFrontend::ScreenProbeTouch(window.GetWidth(),window.GetHeight(),pointer.x,pointer.y);''')
 edit(inp,'  if ((!RetunedFrontend::ScreenProbeEnabled() ||', '''  if(RetunedFrontend::AndroidDualProbeRequested() && RetunedFrontend::ProbeGuestDualActive.load() && !hostGuiVisible){
    const auto value=RetunedFrontend::AndroidLowerTouch.load();
    frame.Hid.TouchPressed=(value&0x80000000u)!=0;frame.Hid.TouchX=(value>>8)&511;frame.Hid.TouchY=value&255;
  }
  if ((!RetunedFrontend::ScreenProbeEnabled() ||''')
 android=root/'ports/android/runtime';(android/'display_jni.cpp').write_bytes((here/'display_jni.cpp').read_bytes())
 edit(android/'CMakeLists.txt','target_sources(oot3d_native_game PRIVATE android_host.cpp)','target_sources(oot3d_native_game PRIVATE android_host.cpp display_jni.cpp)')
 cmake=android/'CMakeLists.txt'
 if 'target_link_libraries(oot3d_native_game PRIVATE android)' not in cmake.read_text():
  cmake.write_text(cmake.read_text()+'\ntarget_link_libraries(oot3d_native_game PRIVATE android)\n')
 edit(android/'CMakeLists.txt','target_include_directories(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}")','target_include_directories(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}" "${root}/runtime/three_ds_recomp/include/fast/oot3d")')
 # include lookup works for both host and renderer translation units.
 (android/'android_secondary_swapchain.h').write_text('#include "fast/oot3d/android_secondary_swapchain.h"\n')
 java=root/'ports/android/app/src/main/java/org/triaevum/android'
 (java/'RetunedDualScreen.java').write_bytes((here/'RetunedDualScreen.java').read_bytes())
 (java/'RetunedEquipmentStrip.java').write_bytes((here/'RetunedEquipmentStrip.java').read_bytes())
 activity=java/'RetunedGameActivity.java'
 edit(activity,'    private TouchOverlay touchOverlay;', '    private TouchOverlay touchOverlay;\n    private RetunedDualScreen dualScreen;')
 edit(activity,'        StartupDiagnostics.stage(this, "loading SDL and game libraries");','''        try {android.system.Os.setenv("RETUNED_SCREEN_PROBE","android-dual",true);android.system.Os.setenv("TRIAEVUM_VULKAN_PRESENT_DISPATCH","graphics",true);}catch(Exception e){throw new RuntimeException(e);}
        StartupDiagnostics.stage(this, "loading SDL and game libraries");''')
 edit(activity,'        retunedTextures=new TextureFolder(this);','        retunedTextures=new TextureFolder(this);\n        dualScreen=new RetunedDualScreen(this);')
 text=activity.read_text()
 if 'if(dualScreen!=null)dualScreen.close();' not in text:
  if 'protected void onDestroy()' in text:
   start=text.index('protected void onDestroy()')
   position=text.index('{',start)+1
   activity.write_text(text[:position]+'if(dualScreen!=null)dualScreen.close();'+text[position:])
  else:
   edit(activity,'    @Override protected void onPause()', '    @Override protected void onDestroy(){if(dualScreen!=null)dualScreen.close();super.onDestroy();}\n\n    @Override protected void onPause()')

if __name__=='__main__':apply(Path(sys.argv[1]))
