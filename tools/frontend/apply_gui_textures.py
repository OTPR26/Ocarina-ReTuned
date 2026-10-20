"""Expose Vulkan GUI images through owned ImGui descriptor sets."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
    root=Path(engine)/'runtime/three_ds_recomp'
    header=root/'include/fast/backends/gfx_vulkan.h'
    edit(header,'    struct TextureRecord {','    struct TextureRecord {\n        VkDescriptorSet GuiDescriptor = VK_NULL_HANDLE;')
    edit(header,'    void DestroyTexture(TextureRecord& texture);','    void DestroyTexture(TextureRecord& texture);\n    void ReleaseGuiTexture(TextureRecord& texture);')
    cpp=root/'src/fast/backends/gfx_vulkan.cpp'
    edit(cpp,'    ImGui_ImplVulkan_Shutdown();','    for (auto& [id, texture] : mTextures) texture.GuiDescriptor = VK_NULL_HANDLE;\n    ImGui_ImplVulkan_Shutdown();')
    edit(cpp,'''ImTextureID GfxRenderingAPIVulkan::GetTextureById(int id) {
    return reinterpret_cast<ImTextureID>(static_cast<intptr_t>(id));
}''','''void GfxRenderingAPIVulkan::ReleaseGuiTexture(TextureRecord& texture) {
    if (texture.GuiDescriptor == VK_NULL_HANDLE) return;
    CheckVk(vkDeviceWaitIdle(mDevice), "vkDeviceWaitIdle(release GUI texture)");
    if (mImGuiInitialized) ImGui_ImplVulkan_RemoveTexture(texture.GuiDescriptor);
    texture.GuiDescriptor = VK_NULL_HANDLE;
}

ImTextureID GfxRenderingAPIVulkan::GetTextureById(int id) {
    const auto found = mTextures.find(static_cast<uint32_t>(id));
    if (found == mTextures.end() || !found->second.Uploaded || !InitImGuiBackend()) return nullptr;
    auto& texture = found->second;
    if (texture.GuiDescriptor == VK_NULL_HANDLE)
        texture.GuiDescriptor = ImGui_ImplVulkan_AddTexture(
            texture.Sampler, texture.View, texture.ImageLayout);
    return reinterpret_cast<ImTextureID>(texture.GuiDescriptor);
}''')
    resources=root/'src/fast/backends/gfx_vulkan_resources.cpp'
    edit(resources,'void GfxRenderingAPIVulkan::RecreateSampler(TextureRecord& texture) {','void GfxRenderingAPIVulkan::RecreateSampler(TextureRecord& texture) {\n    ReleaseGuiTexture(texture);')
    edit(resources,'void GfxRenderingAPIVulkan::DestroyTexture(TextureRecord& texture) {','void GfxRenderingAPIVulkan::DestroyTexture(TextureRecord& texture) {\n    ReleaseGuiTexture(texture);')
