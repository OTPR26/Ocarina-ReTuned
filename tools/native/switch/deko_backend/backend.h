// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "fast/backends/gfx_rendering_api.h"
#include <memory>
struct ImDrawData;
namespace Fast {
class GfxRenderingAPIDeko final : public GfxRenderingAPI {
public:
    GfxRenderingAPIDeko();
    ~GfxRenderingAPIDeko() override;
    const char* GetName() override;
    int GetMaxTextureSize() override;
    GfxClipParameters GetClipParameters() override;
    void UnloadShader(ShaderProgram* oldPrg) override;
    void LoadShader(ShaderProgram* newPrg) override;
    ShaderProgram* CreateAndLoadNewShader(uint64_t shaderId0, uint64_t shaderId1) override;
    ShaderProgram* LookupShader(uint64_t shaderId0, uint64_t shaderId1) override;
    void ShaderGetInfo(ShaderProgram* prg, uint8_t* numInputs, bool usedTextures[2]) override;
    void ClearShaderCache() override;
    uint32_t NewTexture() override;
    void SelectTexture(int tile, uint32_t textureId) override;
    void UploadTexture(const uint8_t* rgba32Buf, uint32_t width, uint32_t height) override;
    void SetSamplerParameters(int sampler, bool linear_filter, uint32_t cms, uint32_t cmt) override;
    bool UploadTextureMipLevel(uint32_t level, const uint8_t* rgba32Buf,
                               uint32_t width, uint32_t height) override;
    bool SetNativeSamplerParameters(int sampler, const GfxNativeSamplerState& state) override;
    void SetDepthTestAndMask(bool depth_test, bool z_upd) override;
    void SetCurrentPrimDepth(float depth) override;
    void SetZmodeDecal(bool decal) override;
    void SetViewport(int x, int y, int width, int height) override;
    void SetScissor(int x, int y, int width, int height) override;
    void SetUseAlpha(bool useAlpha) override;
    bool SetNativeBlendState(const GfxNativeBlendState& state) override;
    bool SetNativeCullMode(GfxNativeCullMode mode) override;
    bool SetOot3dNativeTransform(const float* row_major_matrix) override;
    bool DrawTrianglesCached(uint64_t cache_id, uint64_t content_version,
                             const float* buf_vbo, size_t buf_vbo_len,
                             size_t buf_vbo_num_tris) override;
    void DrawTriangles(float buf_vbo[], size_t buf_vbo_len, size_t buf_vbo_num_tris) override;
    void Init() override;
    void Shutdown() override;
    void OnResize() override;
    void StartFrame() override;
    void EndFrame() override;
    void FinishRender() override;
    int CreateFramebuffer() override;
    void UpdateFramebufferParameters(int fb_id, uint32_t width, uint32_t height, uint32_t msaa_level,
                                     bool opengl_invertY, bool render_target, bool has_depth_buffer,
                                     bool can_extract_depth) override;
    bool UpdateFramebufferParametersWithColorFormat(int fb_id, uint32_t width, uint32_t height,
                                                    uint32_t msaa_level, bool opengl_invertY,
                                                    bool render_target, bool has_depth_buffer,
                                                    bool can_extract_depth,
                                                    GfxFramebufferColorFormat color_format) override;
    bool SupportsOot3dShadow2dR32uiPipeline() const override;
    bool BindOot3dShadow2dTexture(int fb_id, uint32_t texture_unit) override;
    bool SetOot3dShadow2dShaderParameters(uint32_t texture_bias, bool orthographic, bool invert) override;
    bool SupportsOot3dPicaFogLut() const override;
    bool SetOot3dPicaFogShaderParameters(const uint32_t* lut_words, size_t lut_word_count,
                                         bool flip, uint64_t state_key) override;
    bool SetOot3dPicaAlphaTestShaderParameters(bool enabled, uint32_t compare_func,
                                               uint8_t reference) override;
    bool SupportsOot3dPicaTexture2() const override;
    GfxNativePicaBackendStats GetNativePicaBackendStats() const noexcept override;
    void SetNativePicaGeometryCacheEnabled(bool enabled) noexcept override;
    bool PublishPicaCompositionSequence(
        const Renderer3ds::PicaCompositionSequenceView& sequence,
        std::string* error = nullptr) override;
    bool SubmitPicaDraw(const GfxNativePicaDrawView& draw,
                        std::string* error = nullptr) override;
    bool SubmitPicaDisplayTransfer(
        const GfxNativePicaDisplayTransferView& transfer,
        std::string* error = nullptr) override;
    bool ClearPicaRenderTarget(
        uint64_t renderTargetNamespace, uint32_t colorPhysicalAddress,
        std::string* error = nullptr) override;
    bool SubmitPicaMemoryFill(
        const GfxNativePicaMemoryFillView& fill,
        std::string* error = nullptr) override;
    bool QueuePicaCompletion(
        uint64_t completionId, std::string* error = nullptr) override;
    std::vector<uint64_t> TakePicaCompletions() override;
    bool ResetPicaState(std::string* error = nullptr) override;
    bool StartOot3dShadow2dDepthEncodePass(int fb_id, uint32_t clear_value) override;
    void EndOot3dShadow2dDepthEncodePass() override;
    bool DrawOot3dShadow2dDepthEncodedTriangles(float buf_vbo[], size_t buf_vbo_len,
                                                size_t buf_vbo_num_tris) override;
    void StartDrawToFramebuffer(int fbId, float noiseScale) override;
    void CopyFramebuffer(int fbDstId, int fbSrcId, int srcX0, int srcY0, int srcX1, int srcY1, int dstX0, int dstY0,
                         int dstX1, int dstY1) override;
    void ClearFramebuffer(bool color, bool depth) override;
    void ClearDepthRegion(int x, int y, int w, int h) override;
    void ReadFramebufferToCPU(int fbId, uint32_t width, uint32_t height, uint16_t* rgba16Buf) override;
    void ResolveMSAAColorBuffer(int fbIdTarger, int fbIdSrc) override;
    std::unordered_map<std::pair<float, float>, uint16_t, hash_pair_ff>
    GetPixelDepth(int fb_id, const std::set<std::pair<float, float>>& coordinates) override;
    void* GetFramebufferTextureId(int fbId) override;
    void SelectTextureFb(int fbId) override;
    void DeleteTexture(uint32_t texId) override;
    void SetTextureFilter(FilteringMode mode) override;
    FilteringMode GetTextureFilter() override;
    void SetSrgbMode() override;
    ImTextureID GetTextureById(int id) override;

    void Present();
    void GuiInit();
    void GuiRender(ImDrawData*);
private:
    struct Impl;
    std::unique_ptr<Impl> state;
};
}
