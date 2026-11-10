std::pair<VkBuffer, VkDeviceSize> GfxRenderingAPIVulkan::StageNativePicaTexture(
    std::span<const uint8_t> pixels) {
    auto& frame = mFrameResources[mCurrentFrame];
    auto& buffers = frame.TextureUploadBuffers;
    VkDeviceSize offset = (frame.TextureUploadBytesUsed + 15U) & ~VkDeviceSize(15U);
    if (buffers.empty() || offset > buffers.back().Size ||
        pixels.size() > buffers.back().Size - offset) {
        // Keep every recorded copy's source alive until this frame's fence completes.
        // Texture bursts must not consume the arena reserved for draw vertices.
        buffers.reserve(buffers.size() + 1U);
        buffers.push_back(CreateBuffer(
            std::max<VkDeviceSize>(8U * 1024U * 1024U, pixels.size()),
            VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            true));
        offset = 0;
    }
    auto& buffer = buffers.back();
    std::memcpy(static_cast<uint8_t*>(buffer.Mapped) + offset, pixels.data(), pixels.size());
    frame.TextureUploadBytesUsed = offset + pixels.size();
    return {buffer.Buffer, offset};
}

void GfxRenderingAPIVulkan::ResetNativePicaTextureUploads(uint32_t frameIndex) {
    auto& frame = mFrameResources[frameIndex];
    // The caller has waited for this slot's fence. Retain one small reusable chunk;
    // release burst allocations instead of retaining a scene's peak staging memory.
    for (size_t i = 1; i < frame.TextureUploadBuffers.size(); ++i)
        DestroyBuffer(frame.TextureUploadBuffers[i]);
    if (frame.TextureUploadBuffers.size() > 1U) frame.TextureUploadBuffers.resize(1U);
    if (!frame.TextureUploadBuffers.empty() &&
        frame.TextureUploadBuffers.front().Size > 8U * 1024U * 1024U) {
        DestroyBuffer(frame.TextureUploadBuffers.front());
        frame.TextureUploadBuffers.clear();
    }
    frame.TextureUploadBytesUsed = 0;
}
