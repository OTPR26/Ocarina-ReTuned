"""Quiesce rendering before mobile operating systems revoke GPU access."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
 root=Path(engine);runtime=root/'tools/oot3d/native_game_runtime';base=root/'runtime/three_ds_recomp'
 (base/'include/fast/oot3d/retuned_mobile_lifecycle.h').write_text(Path(__file__).with_name('mobile_lifecycle.h').read_text())
 edit(base/'include/fast/backends/gfx_rendering_api.h','    virtual void FinishRender() = 0;','    virtual void FinishRender() = 0;\n    virtual void WaitForIdle() {}')
 edit(base/'include/fast/backends/gfx_rendering_api.h','    virtual void WaitForIdle() {}','    virtual void WaitForIdle() {}\n    virtual void ResumeFromBackground() { OnResize(); }')
 edit(base/'include/fast/backends/gfx_vulkan.h','    void FinishRender() override;','    void FinishRender() override;\n    void WaitForIdle() override;')
 edit(base/'include/fast/backends/gfx_vulkan.h','    void WaitForIdle() override;','    void WaitForIdle() override;\n    void ResumeFromBackground() override;')
 edit(base/'include/fast/backends/gfx_vulkan.h','    bool mSwapchainDirty = false;','    bool mSwapchainDirty = false;\n    bool mSurfaceNeedsRefresh = false;')
 device=base/'src/fast/backends/gfx_vulkan_device.cpp'
 edit(device,'    DestroySwapchainResources();\n    CreateSwapchainResources();',      '    DestroySwapchainResources();\n    if(mSurfaceNeedsRefresh) {\n        if(mSurface!=VK_NULL_HANDLE)vkDestroySurfaceKHR(mInstance,mSurface,nullptr);\n        mSurface=VK_NULL_HANDLE;\n        CreateSurface();\n        mSurfaceNeedsRefresh=false;\n    }\n    CreateSwapchainResources();')
 vulkan=base/'src/fast/backends/gfx_vulkan.cpp'
 old=vulkan.read_text()
 old=old.replace('void GfxRenderingAPIVulkan::WaitForIdle() {\n    if(mDevice', 'void GfxRenderingAPIVulkan::WaitForIdle() {\n    WaitForAllPresents();\n    if(mDevice')
 vulkan.write_text(old)
 if 'void GfxRenderingAPIVulkan::WaitForIdle()' not in vulkan.read_text():
  edit(vulkan,'void GfxRenderingAPIVulkan::OnResize() {','void GfxRenderingAPIVulkan::WaitForIdle() {\n    WaitForAllPresents();\n    if(mDevice!=VK_NULL_HANDLE)CheckVk(vkDeviceWaitIdle(mDevice),"vkDeviceWaitIdle(background)");\n}\n\nvoid GfxRenderingAPIVulkan::OnResize() {')
 if 'void GfxRenderingAPIVulkan::ResumeFromBackground()' not in vulkan.read_text():
  edit(vulkan,'void GfxRenderingAPIVulkan::OnResize() {','void GfxRenderingAPIVulkan::ResumeFromBackground() {\n#ifdef __ANDROID__\n    mSurfaceNeedsRefresh=true;\n    if(mPresentError.load()==VK_ERROR_SURFACE_LOST_KHR)mPresentError=VK_SUCCESS;\n#endif\n    OnResize();\n}\n\nvoid GfxRenderingAPIVulkan::OnResize() {')
 header=runtime/'oot3d_native_a32_window_session.h'
 edit(header,'#pragma once','#pragma once\n#include "fast/oot3d/retuned_mobile_lifecycle.h"')
 edit(header,'  std::optional<GuiRendererRoutingReset> guiRendererRoutingReset;','  std::optional<GuiRendererRoutingReset> guiRendererRoutingReset;\n  std::unique_ptr<RetunedFrontend::MobileLifecycleGate> mobileLifecycle;')
 setup=runtime/'oot3d_native_a32_window_setup.cpp'
 setup.write_text(setup.read_text().replace('apiPointer->OnResize();realtimePacerStorage->ResetDeadline();','apiPointer->ResumeFromBackground();realtimePacerStorage->ResetDeadline();'))
 edit(setup,'  guiRendererRoutingReset.emplace(parallelPresentation ? fast3dGui : nullptr);','''  guiRendererRoutingReset.emplace(parallelPresentation ? fast3dGui : nullptr);
#if defined(__IOS__) || defined(__ANDROID__)
  mobileLifecycle=std::make_unique<RetunedFrontend::MobileLifecycleGate>(
    [&]{renderStream.Run([&]{apiPointer->WaitForIdle();});},
    [&]{renderStream.Run([&]{apiPointer->ResumeFromBackground();realtimePacerStorage->ResetDeadline();});});
#endif''')
 frame=runtime/'oot3d_native_a32_window_frame.cpp'
 edit(frame,'  WindowDemoFrameTiming frameTiming;','''  WindowDemoFrameTiming frameTiming;
  if(mobileLifecycle && !mobileLifecycle->Active()) {
    window.HandleEvents();
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    const auto now=std::chrono::steady_clock::now();
    timing.LastTime=now;lastPresentationTime=now;lastCompletedFrameTime=now;
    return true;
  }''')
 edit(frame,'  const auto requestedPresentationPolicy =','  if(mobileLifecycle && !mobileLifecycle->Active())return true;\n  const auto requestedPresentationPolicy =')
