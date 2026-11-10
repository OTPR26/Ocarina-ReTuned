"""Keep Vulkan texture staging independent of the fixed draw-vertex arena."""
from pathlib import Path


def apply(root):
    base = Path(root) / 'runtime/three_ds_recomp'
    def edit(name, before, after):
        path = base / name
        source = path.read_text()
        if after in source:
            return
        if source.count(before) != 1:
            raise ValueError('Texture staging context changed: ' + name)
        path.write_text(source.replace(before, after))

    header = 'include/fast/backends/gfx_vulkan.h'
    edit(header, '        std::vector<BufferAllocation> RetiredUniformBuffers;',
         '        std::vector<BufferAllocation> RetiredUniformBuffers;\n'
         '        std::vector<BufferAllocation> TextureUploadBuffers;\n'
         '        VkDeviceSize TextureUploadBytesUsed = 0;')
    edit(header, '    void DestroyBuffer(BufferAllocation& buffer);',
         '    void DestroyBuffer(BufferAllocation& buffer);\n'
         '    std::pair<VkBuffer, VkDeviceSize> StageNativePicaTexture(std::span<const uint8_t> pixels);\n'
         '    void ResetNativePicaTextureUploads(uint32_t frameIndex);')
    source = 'src/fast/backends/'
    old = '''    auto& frame = mFrameResources[mCurrentFrame];
    const VkDeviceSize uploadOffset = (frame.VertexBytesUsed + 15U) & ~VkDeviceSize(15U);
    if (uploadOffset + pixels.size() > frame.VertexBuffer.Size)
        throw std::runtime_error("native PICA texture exceeds the per-frame upload arena");
    std::memcpy(static_cast<uint8_t*>(frame.VertexBuffer.Mapped) + uploadOffset,
                pixels.data(), pixels.size());
    frame.VertexBytesUsed = uploadOffset + pixels.size();'''
    edit(source + 'gfx_vulkan_pica_textures.cpp', old,
         '    const auto [uploadBuffer, uploadOffset] = StageNativePicaTexture(pixels);')
    edit(source + 'gfx_vulkan_pica_textures.cpp',
         'vkCmdCopyBufferToImage(commandBuffer, frame.VertexBuffer.Buffer, texture.Image,',
         'vkCmdCopyBufferToImage(commandBuffer, uploadBuffer, texture.Image,')
    edit(source + 'gfx_vulkan_resources.cpp', 'namespace Fast {\n',
         'namespace Fast {\n\n#include "retuned_texture_upload.inc"\n')
    (base / source / 'retuned_texture_upload.inc').write_text(
        Path(__file__).with_name('vulkan_texture_upload.inc').read_text())
    edit(source + 'gfx_vulkan_frame.cpp',
         '    frame.RetiredUniformBuffers.clear();',
         '    frame.RetiredUniformBuffers.clear();\n    ResetNativePicaTextureUploads(mCurrentFrame);')
    edit(source + 'gfx_vulkan_lifecycle.cpp',
         '            frame.RetiredUniformBuffers.clear();',
         '            frame.RetiredUniformBuffers.clear();\n'
         '            for (auto& buffer : frame.TextureUploadBuffers) DestroyBuffer(buffer);\n'
         '            frame.TextureUploadBuffers.clear();')
    # Buffer allocation can fail after creating its Vulkan handle or memory.
    # Roll back partially created staging resources before propagating the error.
    edit(source + 'gfx_vulkan_resources.cpp',
         '    VkBufferCreateInfo bufferInfo{ VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };',
         '    try {\n    VkBufferCreateInfo bufferInfo{ VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };')
    edit(source + 'gfx_vulkan_resources.cpp',
         '    return buffer;\n}\n\nvoid GfxRenderingAPIVulkan::DestroyBuffer',
         '    return buffer;\n    } catch (...) {\n        DestroyBuffer(buffer);\n        throw;\n    }\n}\n\nvoid GfxRenderingAPIVulkan::DestroyBuffer')
