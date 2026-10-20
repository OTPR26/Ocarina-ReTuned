"""Add excluded-rectangle clipping to native Vulkan draw submission."""
from pathlib import Path
import argparse
from apply_native_port import edit

def apply(engine):
    include=engine/'runtime/three_ds_recomp/include/fast/renderer3ds/exclude_scissor.h'
    include.write_text(Path(__file__).with_name('exclude_scissor.h').read_text())
    draw=engine/'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_pica_draw.cpp'
    edit(draw, '#include "gfx_vulkan_pica_internal.h"', '#include "gfx_vulkan_pica_internal.h"\n#include "fast/renderer3ds/exclude_scissor.h"')
    edit(draw, '''        if (draw.ScissorMode == 1U) {
            throw std::runtime_error(
                "native PICA exclude scissor requires shader emulation");
        }
        if (draw.ScissorMode != 0U && draw.ScissorMode != 3U) {''',
         '''        if (draw.ScissorMode != 0U && draw.ScissorMode != 1U && draw.ScissorMode != 3U) {''')
    edit(draw, '''            const bool fullTargetRaster =
                compositionDomain ==''', '''            const bool fullTargetRaster =
                draw.ScissorMode != 1U &&
                compositionDomain ==''')
    pipelines=draw.with_name('gfx_vulkan_pica_pipelines.cpp')
    edit(pipelines,'    attributes.reserve(draw.VertexAttributes.size());',
         '    attributes.reserve(draw.VertexAttributes.size());\n    bool nativeVertexFormatsSupported = true;')
    edit(pipelines,'            throw std::runtime_error(\n                "native PICA vertex format is not supported by this GPU");',
         '            nativeVertexFormatsSupported = false;')
    edit(pipelines,'    EnsureNativePicaVulkanShaderModules(draw, shader);',
         '    if (!nativeVertexFormatsSupported)\n        throw std::runtime_error("native PICA vertex format is not supported by the Vulkan fallback");\n    EnsureNativePicaVulkanShaderModules(draw, shader);')
    before='''        // Coverage runs before the native draw: stencil must still have its'''
    start='''        const VkRect2D originalScissor = mScissor;
        Retuned::ScissorParts scissorParts;
        scissorParts.Rects[0] = {mScissor.offset.x, mScissor.offset.y, mScissor.extent.width, mScissor.extent.height};
        scissorParts.Count = mScissor.extent.width && mScissor.extent.height ? 1U : 0U;
        if (draw.ScissorMode == 1U) {
            const uint32_t x2 = uint32_t{draw.ScissorX2} + 1U;
            const uint32_t y2 = uint32_t{draw.ScissorY2} + 1U;
            const Retuned::ScissorRect hole{
                static_cast<int32_t>(rasterCanvas.X + draw.ScissorX1 * framebufferScaleX),
                static_cast<int32_t>(rasterCanvas.Y + draw.ScissorY1 * framebufferScaleY),
                static_cast<uint32_t>((x2 > draw.ScissorX1 ? x2 - draw.ScissorX1 : 0U) * framebufferScaleX),
                static_cast<uint32_t>((y2 > draw.ScissorY1 ? y2 - draw.ScissorY1 : 0U) * framebufferScaleY)};
            scissorParts = Retuned::ExcludeScissor(scissorParts.Rects[0], hole);
        }
        bool nriOwnedDrawBound = false, nriPipelineBound = false;
        for (uint32_t partIndex = 0; partIndex < scissorParts.Count; ++partIndex) {
            const auto part = scissorParts.Rects[partIndex];
            mScissor = {{part.X, part.Y}, {part.Width, part.Height}};
            nriDraw.Scissor = mScissor;
'''
    edit(draw,before,start+before)
    edit(draw,'''        const bool nriOwnedDrawBound =
            nriOwnedDraw &&''','''        nriOwnedDrawBound =
            nriOwnedDraw &&''')
    edit(draw,'''        bool nriPipelineBound = nriOwnedDrawBound;''','''        nriPipelineBound = nriOwnedDrawBound;''')
    edit(draw,'''        if (coveragePipeline != nullptr) {
            ++mDrawCallCountThisFrame;''','''        }
        mScissor = originalScissor;
        if (coveragePipeline != nullptr) {
            ++mDrawCallCountThisFrame;''')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine',type=Path)
    apply(parser.parse_args().engine)
