"""Quiesce rendering before mobile operating systems revoke GPU access."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
 root=Path(engine);runtime=root/'tools/oot3d/native_game_runtime';base=root/'runtime/three_ds_recomp'
 (base/'include/fast/oot3d/retuned_mobile_lifecycle.h').write_text(Path(__file__).with_name('mobile_lifecycle.h').read_text())
 edit(base/'include/fast/backends/gfx_rendering_api.h','    virtual void FinishRender() = 0;','    virtual void FinishRender() = 0;\n    virtual void WaitForIdle() {}')
 edit(base/'include/fast/backends/gfx_vulkan.h','    void FinishRender() override;','    void FinishRender() override;\n    void WaitForIdle() override;')
 vulkan=base/'src/fast/backends/gfx_vulkan.cpp'
 old=vulkan.read_text()
 old=old.replace('void GfxRenderingAPIVulkan::WaitForIdle() {\n    if(mDevice', 'void GfxRenderingAPIVulkan::WaitForIdle() {\n    WaitForAllPresents();\n    if(mDevice')
 vulkan.write_text(old)
 edit(vulkan,'void GfxRenderingAPIVulkan::OnResize() {','void GfxRenderingAPIVulkan::WaitForIdle() {\n    WaitForAllPresents();\n    if(mDevice!=VK_NULL_HANDLE)CheckVk(vkDeviceWaitIdle(mDevice),"vkDeviceWaitIdle(background)");\n}\n\nvoid GfxRenderingAPIVulkan::OnResize() {')
 header=runtime/'oot3d_native_a32_window_session.h'
 edit(header,'#pragma once','#pragma once\n#include "fast/oot3d/retuned_mobile_lifecycle.h"')
 edit(header,'  std::optional<GuiRendererRoutingReset> guiRendererRoutingReset;','  std::optional<GuiRendererRoutingReset> guiRendererRoutingReset;\n  std::unique_ptr<RetunedFrontend::MobileLifecycleGate> mobileLifecycle;')
 setup=runtime/'oot3d_native_a32_window_setup.cpp'
 edit(setup,'  guiRendererRoutingReset.emplace(parallelPresentation ? fast3dGui : nullptr);','''  guiRendererRoutingReset.emplace(parallelPresentation ? fast3dGui : nullptr);
#if defined(__IOS__) || defined(__ANDROID__)
  mobileLifecycle=std::make_unique<RetunedFrontend::MobileLifecycleGate>(
    [&]{renderStream.Run([&]{apiPointer->WaitForIdle();});},
    [&]{renderStream.Run([&]{apiPointer->OnResize();realtimePacerStorage->ResetDeadline();});});
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
