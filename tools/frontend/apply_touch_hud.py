"""Position the user's live Reframed HUD geometry over native touch controls."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
 root=Path(engine);source=Path(__file__).parent;runtime=root/'tools/oot3d/native_game_runtime'
 (runtime/'retuned_touch_hud_runtime.h').write_text((source/'touch_hud_runtime.h').read_text())
 setup=runtime/'oot3d_native_a32_window_setup.cpp'
 previous=setup.read_text().replace('  wholeAotObservableExitBlocks.insert(wholeAotObservableExitBlocks.end(),touchHudHooks.begin(),touchHudHooks.end());\n  std::sort(wholeAotObservableExitBlocks.begin(),','  wholeAotObservableExitBlocks.insert(wholeAotObservableExitBlocks.end(),touchHudHooks.begin(),touchHudHooks.end());\n  std::sort(blockEntryHooks.begin(),blockEntryHooks.end());\n  blockEntryHooks.erase(std::unique(blockEntryHooks.begin(),blockEntryHooks.end()),blockEntryHooks.end());\n  std::sort(wholeAotObservableExitBlocks.begin(),')
 setup.write_text(previous)
 edit(setup,'  blockEntryHooks = std::vector<uint32_t>{','  const auto touchHudHooks=RetunedFrontend::InitializeTouchHudBridge(launch.A32ProcessManifestPath);\n  blockEntryHooks = std::vector<uint32_t>{')
 edit(setup,'  std::sort(wholeAotObservableExitBlocks.begin(),','''  blockEntryHooks.insert(blockEntryHooks.end(),touchHudHooks.begin(),touchHudHooks.end());
  wholeAotObservableExitBlocks.insert(wholeAotObservableExitBlocks.end(),touchHudHooks.begin(),touchHudHooks.end());
  std::sort(blockEntryHooks.begin(),blockEntryHooks.end());
  blockEntryHooks.erase(std::unique(blockEntryHooks.begin(),blockEntryHooks.end()),blockEntryHooks.end());
  std::sort(wholeAotObservableExitBlocks.begin(),''')
 dispatch=runtime/'oot3d_native_a32_candidate_dispatch.cpp'
 marker='#include "retuned_touch_hud_runtime.h"'
 if marker not in dispatch.read_text():dispatch.write_text(marker+'\n'+dispatch.read_text())
 text=dispatch.read_text();at=text.index('bool ExecuteProductTopScreenHook(');prefix=text[:at];tail=text[at:]
 before='  // Extended draw distance object slots, in every UI profile. Their entries'
 after= '''  auto& touchHud=RetunedFrontend::NativeTouchHud;
  if(touchHud.Ready()&&dispatch.Memory && (pc==touchHud.Upload||pc==touchHud.PrepareAction)) {
    runBlockEntry();
    if(pc==touchHud.Upload){
      RetunedFrontend::TouchHudLive=state.r[0]!=0&&touchHud.Gameplay(*dispatch.Memory)&&RetunedFrontend::ValidTouchHudAnchors(RetunedFrontend::SnapshotTouchHud());
      if(state.r[0]!=0)touchHud.PlaceItems(*dispatch.Memory);
    }
    const auto returnPc=state.r[14];
    const bool handled=Oot3dNativeGame::ExecuteOot3dCompiledFunction(
        pc,state,*dispatch.Memory,result,blockBudget,blocksConsumed,
        dispatch.BlockEntry,dispatch.BlockEntryUser,
        dispatch.BlockEntryPcs.data(),dispatch.BlockEntryPcs.size(),true,true,true,returnPc);
    if(handled&&pc==touchHud.PrepareAction&&result->pc==returnPc)touchHud.PlaceAction(*dispatch.Memory);
    return handled;
  }
  // Extended draw distance object slots, in every UI profile. Their entries'''
 begins=[tail.find(x) for x in ('  auto& touchHud=RetunedFrontend::NativeTouchHud;', '  const auto& touchHud=RetunedFrontend::NativeTouchHud;')]
 begin=min((x for x in begins if x>=0),default=-1)
 if begin>=0:
  end=tail.index(before,begin)
  tail=tail[:begin]+tail[end:]
  dispatch.write_text(prefix+tail)
 if after not in tail:
  if tail.count(before)!=1:raise ValueError('Product UI dispatch context changed')
  dispatch.write_text(prefix+tail.replace(before,after))
 backend=root/'runtime/three_ds_recomp/include/fast'
 edit(backend/'oot3d/title_render_backend.h','    virtual bool PrepareOverlay(std::string* = nullptr) {',      '    virtual std::array<uint32_t,2> OverlayOutputSize() const noexcept { return {}; }\n    virtual bool PrepareOverlay(std::string* = nullptr) {')
 edit(backend/'backends/gfx_vulkan.h','    bool PrepareOverlay(',      '    std::array<uint32_t,2> OverlayOutputSize() const noexcept override { return {mSwapchainExtent.width,mSwapchainExtent.height}; }\n    bool PrepareOverlay(')
 renderer=root/'tools/oot3d/ui_n64'
 edit(renderer/'oot3d_n64_ui_renderer.h','    NativeTopScreen400x240,','    NativeTopScreen400x240,\n    FullWindow400x240,')
 edit(renderer/'oot3d_n64_ui_renderer.cpp','canvasMode == N64UiCanvasMode::NativeTopScreen400x240','(canvasMode == N64UiCanvasMode::NativeTopScreen400x240 || canvasMode == N64UiCanvasMode::FullWindow400x240)')
 edit(renderer/'oot3d_n64_ui_renderer.cpp','    const auto viewport = Oot3d::Renderer::FitUiPresentationViewport(\n        width, height, canvasWidth, kCanvasHeight);','    const auto viewport = canvasMode == N64UiCanvasMode::FullWindow400x240\n        ? Oot3d::Renderer::FitUiPresentationViewport(width,height,float(width),float(height))\n        : Oot3d::Renderer::FitUiPresentationViewport(width, height, canvasWidth, kCanvasHeight);')
 provider=runtime/'oot3d_native_ui_texture_provider.cpp'
 edit(provider,'    const bool generatedText = identity.semantic_name == "oot3d/native/generated_text";',
      '    const bool touchHud = identity.semantic_name == "oot3d/native/retuned_touch_hud";\n    const bool generatedText = identity.semantic_name == "oot3d/native/generated_text";')
 edit(provider,'auto descriptor = generatedText ?','auto descriptor = (generatedText || touchHud) ?')
 edit(provider,'if (!generatedText && !descriptor.has_value())','if (!generatedText && !touchHud && !descriptor.has_value())')
 edit(provider,'    if (generatedText) {\n        constexpr std::array', '    if (generatedText || touchHud) {\n        constexpr std::array')
 edit(provider,'runtimeWidth > 1024 || runtimeHeight > 1024 ||','runtimeWidth > (touchHud ? 4096 : 1024) || runtimeHeight > (touchHud ? 4096 : 1024) ||')
 frame=runtime/'oot3d_native_a32_window_frame.cpp'
 edit(frame,'  CpuProbe::Scope cpuPresent(CpuProbe::Phase::Present);','''  if(RetunedFrontend::TouchHudActive.load()&&RetunedFrontend::TouchHudLive.load()) {
    if(auto atlas=uiLifecycleBridge.NativePauseSharedTextureIdentity(oot3d::ui::UiPauseSharedTextureSlot::CameraInterface)) {
      atlas->semantic_name="oot3d/native/retuned_touch_hud";
      auto actionAtlas=uiLifecycleBridge.NativePauseSharedTextureIdentity(oot3d::ui::UiPauseSharedTextureSlot::HudAtlas);
      if(actionAtlas)actionAtlas->semantic_name="oot3d/native/retuned_touch_hud";
      auto icons=RetunedFrontend::NativeTouchHud.Overlay(process.Memory(),*atlas,actionAtlas?&*actionAtlas:nullptr);
      auto prepared=n64UiRenderer.PrepareTextures(icons);
      renderStream.Submit([&,icons=std::move(icons),prepared=std::move(prepared),width,height]()mutable{
        if(rendererFrameSkipped){n64UiRenderer.Stage(std::move(prepared));return;}
        auto output=titleRenderBackend?titleRenderBackend->OverlayOutputSize():std::array<uint32_t,2>{};
        if(!output[0]||!output[1])output={width,height};
        if(!n64UiRenderer.Render(icons,output[0],output[1],oot3d::ui::N64UiCanvasMode::FullWindow400x240,std::move(prepared),&renderError))
          throw std::runtime_error("Touch item overlay failed: "+renderError);
      });
    }
  }
  CpuProbe::Scope cpuPresent(CpuProbe::Phase::Present);''')
