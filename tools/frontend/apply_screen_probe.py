"""Install an opt-in, single-window two-view rendering/input proof."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reframed'))
from apply_native_port import edit

def apply(engine):
 engine=Path(engine);source=Path(__file__).parent
 include=engine/'runtime/three_ds_recomp/include/fast/oot3d'
 for name in ('screen_probe.h',):
  (include/('retuned_'+name)).write_text((source/name).read_text())
 for name in ('screen_layout.h','screen_presentation_bridge.h','screen_mode_policy.h','duo_game_display.h'):
  (include/name).write_bytes((source/name).read_bytes())
 (include/'retuned_screen_layout.h').write_text('#pragma once\n#include "screen_layout.h"\n')
 backend=engine/'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_pica_display.cpp'
 text=backend.read_text();marker='#include "fast/oot3d/retuned_screen_probe.h"\n'
 if marker not in text:backend.write_text(marker+text)
 for filename in ('gfx_vulkan_pica.cpp','gfx_vulkan_frame.cpp','gfx_vulkan_pica_draw.cpp','gfx_vulkan_pica_display.cpp'):
  path=backend.parent/filename;text=path.read_text()
  if marker not in text:text=marker+text
  text=text.replace('{mSwapchainExtent.width, mSwapchainExtent.height}',
      '{RetunedFrontend::ProbeOutputWidth(mSwapchainExtent.width,mSwapchainExtent.height), RetunedFrontend::ProbeOutputHeight(mSwapchainExtent.width,mSwapchainExtent.height)}')
  path.write_text(text)
 edit(backend,'''        const bool alphaOverlay = !copyBoundary &&
            transfer.PresentationMode ==
                GfxNativePicaPresentationMode::AlphaOverlay;''','''        const bool alphaOverlay = !copyBoundary &&
            (transfer.PresentationMode == GfxNativePicaPresentationMode::AlphaOverlay ||
             (RetunedFrontend::ScreenProbeEnabled() &&
              RetunedFrontend::ProbeScanoutScreen == RetunedFrontend::GameScreen::Lower));''')
 edit(backend,'''        const auto presentation = FitNativePicaPresentation(
            mSwapchainExtent.width, mSwapchainExtent.height,
            static_cast<float>(display.Height),
            static_cast<float>(display.Width));''','''        auto presentation = FitNativePicaPresentation(
            mSwapchainExtent.width, mSwapchainExtent.height,
            static_cast<float>(display.Height),
            static_cast<float>(display.Width));
        if(RetunedFrontend::ScreenProbeEnabled()) {
            const auto screens=RetunedFrontend::ScreenProbeLayout(
                mSwapchainExtent.width,mSwapchainExtent.height);
            const auto bounds=RetunedFrontend::ProbeScanoutScreen==RetunedFrontend::GameScreen::Lower?screens.Lower:screens.Top;
            const auto fitted=RetunedFrontend::FitScreen(bounds,float(display.Height)/std::max(1.f,float(display.Width)));
            presentation.X=fitted.X;presentation.Y=fitted.Y;
            presentation.Width=fitted.Width;presentation.Height=fitted.Height;
        }''')
 runtime=engine/'tools/oot3d/native_game_runtime'
 frame=runtime/'oot3d_native_a32_window_frame.cpp'
 text=frame.read_text()
 if marker not in text:frame.write_text(marker+text)
 edit(frame,'''    const bool presentNativeBottomFrontend =
        Oot3dNativeGame::ShouldPresentNativeBottomFrontend(''','''    const bool presentNativeBottomFrontend = RetunedFrontend::ScreenProbeEnabled() ||
        Oot3dNativeGame::ShouldPresentNativeBottomFrontend(''')
 before='''            [&, bottomSelection = selectedBottom->second] {
              if (rendererFrameSkipped ||
                  !picaPresentationScheduler.HasSnapshot(
                      bottomSelection,
                      presentationRenderTargetNamespace)) {
                return;
              }
              if (!picaPresentationScheduler.PresentExisting(
                      api, bottomSelection,
                      presentationRenderTargetNamespace, &renderError)) {'''
 after='''            [&, bottomSelection = selectedBottom->second] {
              RetunedFrontend::ProbeScanoutScope probeScope(RetunedFrontend::GameScreen::Lower);
              if (RetunedFrontend::ScreenProbeEnabled() &&
                  RetunedFrontend::ScreenProbeLayout(1,1).Lower.Width<=0) return;
              auto bottomNamespace=presentationRenderTargetNamespace;
              if(RetunedFrontend::ScreenProbeEnabled() &&
                 !picaPresentationScheduler.HasSnapshot(bottomSelection,bottomNamespace))
                bottomNamespace=kNativeDependencyRenderTargetNamespace;
              if (rendererFrameSkipped ||
                  !picaPresentationScheduler.HasSnapshot(bottomSelection,bottomNamespace)) {
                return;
              }
              if (!picaPresentationScheduler.PresentExisting(
                      api, bottomSelection,
                      bottomNamespace, &renderError)) {'''
 # Upgrade a previous revision of this opt-in block in an isolated tree.
 text=frame.read_text()
 old='              auto bottomNamespace=presentationRenderTargetNamespace;'
 guard='              if (RetunedFrontend::ScreenProbeEnabled() &&\n                  RetunedFrontend::ScreenProbeLayout(1,1).Lower.Width<=0) return;\n'
 if old in text and guard not in text:frame.write_text(text.replace(old,guard+old))
 edit(frame,before,after)
 setup=runtime/'oot3d_native_a32_window_setup.cpp';text=setup.read_text()
 if marker not in text:setup.write_text(marker+text)
 edit(setup,'''  widescreenProjection.Projection.Presentation =
      Fast::Oot3d::ResolveScenePresentationPolicy(
          std::max<uint32_t>(1, window.GetWidth()),
          std::max<uint32_t>(1, window.GetHeight()));''','''  const auto probeTop=RetunedFrontend::ScreenProbeLayout(window.GetWidth(),window.GetHeight()).Top;
  widescreenProjection.Projection.Presentation =
      Fast::Oot3d::ResolveScenePresentationPolicy(
          RetunedFrontend::ScreenProbeEnabled()?std::max<uint32_t>(1,static_cast<uint32_t>(probeTop.Width)):std::max<uint32_t>(1, window.GetWidth()),
          RetunedFrontend::ScreenProbeEnabled()?std::max<uint32_t>(1,static_cast<uint32_t>(probeTop.Height)):std::max<uint32_t>(1, window.GetHeight()));''')
 inp=runtime/'oot3d_native_a32_window_input.cpp';text=inp.read_text()
 if marker not in text:inp.write_text(marker+text)
 edit(inp,'''  const bool gameplayMouseEligible = ResolveNativeGameplayMouseOwnership(''','''  const bool gameplayMouseEligible = !RetunedFrontend::ScreenProbeEnabled() && ResolveNativeGameplayMouseOwnership(''')
 # Upgrade only our previous opt-in touch block, retaining applier idempotence.
 text=inp.read_text()
 text=text.replace('if(RetunedFrontend::ScreenProbeEnabled() && !hostGuiVisible) {',
                   'if(RetunedFrontend::ScreenProbeEnabled() && (!RetunedFrontend::DuoProbeRequested() || RetunedFrontend::ProbeGuestDualActive.load()) && !hostGuiVisible) {')
 text=text.replace('if (!RetunedFrontend::ScreenProbeEnabled() && nativeFrontendTouchEnabled && !hostGuiVisible) {',
                   'if ((!RetunedFrontend::ScreenProbeEnabled() || (RetunedFrontend::DuoProbeRequested() && !RetunedFrontend::ProbeGuestDualActive.load())) && nativeFrontendTouchEnabled && !hostGuiVisible) {')
 text=text.replace('    const auto layout=RetunedFrontend::ScreenProbeLayout(window.GetWidth(),window.GetHeight());\n','')
 text=text.replace('const auto touch=RetunedFrontend::MapLowerScreenTouch(layout,pointer.x,pointer.y);',
                   'const auto touch=RetunedFrontend::ScreenProbeTouch(window.GetWidth(),window.GetHeight(),pointer.x,pointer.y);')
 inp.write_text(text)
 edit(inp,'''  if (nativeFrontendTouchEnabled && !hostGuiVisible) {''','''  if(RetunedFrontend::ScreenProbeEnabled() && (!RetunedFrontend::DuoProbeRequested() || RetunedFrontend::ProbeGuestDualActive.load()) && !hostGuiVisible) {
    if(window.IsMouseCaptured())window.SetMouseCapture(false);
    window.SetCursorVisibility(true);
    const auto pointer=window.GetMousePos();
    const auto touch=RetunedFrontend::ScreenProbeTouch(window.GetWidth(),window.GetHeight(),pointer.x,pointer.y);
    frame.Hid.TouchPressed=touch.has_value() && window.GetMouseState(Ship::LUS_MOUSE_BTN_LEFT);
    frame.Hid.TouchX=touch?touch->X:0;frame.Hid.TouchY=touch?touch->Y:0;
  }
  if ((!RetunedFrontend::ScreenProbeEnabled() || (RetunedFrontend::DuoProbeRequested() && !RetunedFrontend::ProbeGuestDualActive.load())) && nativeFrontendTouchEnabled && !hostGuiVisible) {''')

if __name__=='__main__':apply(Path(sys.argv[1]))
