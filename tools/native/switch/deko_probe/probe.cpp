// SPDX-License-Identifier: GPL-2.0-or-later
// Isolated GPU/readback test; fixtures are generated locally and never
// distributed.
#include "probe_fixtures.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deko3d.h>
#include <stdexcept>
#include <string>
#include <switch.h>
#include <sys/stat.h>
#include <vector>
namespace {
constexpr unsigned W = 256, H = 256, CodeSize = 8 * 1024 * 1024,
                   CmdSize = 256 * 1024;
constexpr unsigned UniformOffset = 0, TextureOffset = 16384,
                   ImageDescriptorOffset = 20480,
                   SamplerDescriptorOffset = 20608, ReadbackOffset = 24576;
FILE *logFile = nullptr;
void Log(const char *text) {
  if (logFile) {
    fprintf(logFile, "%s\n", text);
    fflush(logFile);
  }
}
void Check(bool ok, const char *error) {
  if (!ok)
    throw std::runtime_error(error);
}
void Debug(void *, const char *where, DkResult result, const char *message) {
  if (logFile) {
    fprintf(logFile, "deko_debug=%d %s: %s\n", int(result), where ? where : "",
            message ? message : "");
    fflush(logFile);
  }
}
unsigned Align(unsigned value, unsigned alignment) {
  return (value + alignment - 1) & ~(alignment - 1);
}
DkDevice device;
DkQueue queue;
DkCmdBuf cmd;
DkSwapchain swapchain;
DkMemBlock codeMem, cmdMem, imageMem, dataMem, textureMem;
DkImage frames[2], texture, integerTexture;
unsigned frameSize, codeOffset = 0;
std::vector<DkShader> shaders;
DkMemBlock Memory(unsigned size, unsigned flags) {
  DkMemBlockMaker m;
  dkMemBlockMakerDefaults(&m, device, Align(size, DK_MEMBLOCK_ALIGNMENT));
  m.flags = flags;
  auto p = dkMemBlockCreate(&m);
  Check(p != nullptr, "memory allocation failed");
  return p;
}
void Submit() {
  auto list = dkCmdBufFinishList(cmd);
  dkQueueSubmitCommands(queue, list);
  DkFence fence;
  dkQueueSignalFence(queue, &fence, true);
  dkQueueFlush(queue);
  Check(dkFenceWait(&fence, 10'000'000'000LL) == DkResult_Success,
        "GPU fence timed out");
  dkCmdBufClear(cmd);
  dkCmdBufAddMemory(cmd, cmdMem, 0, CmdSize);
}
void LoadModule(size_t index) {
  std::string path =
      std::string("sdmc:/switch/retuned-deko-probe/modules/") + kModules[index];
  FILE *f = fopen(path.c_str(), "rb");
  Check(f != nullptr, "module file missing");
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  rewind(f);
  Check(size >= 512 && size <= 1024 * 1024, "module extent invalid");
  Check(codeOffset + Align(size, DK_SHADER_CODE_ALIGNMENT) <
            CodeSize - DK_SHADER_CODE_UNUSABLE_SIZE,
        "code arena full");
  auto *p =
      static_cast<unsigned char *>(dkMemBlockGetCpuAddr(codeMem)) + codeOffset;
  size_t read = fread(p, 1, size, f);
  fclose(f);
  Check(read == size, "module read truncated");
  Check(memcmp(p, "DKSH", 4) == 0, "module magic invalid");
  DkShaderMaker m;
  dkShaderMakerDefaults(&m, codeMem, codeOffset);
  dkShaderInitialize(&shaders[index], &m);
  Check(dkShaderIsValid(&shaders[index]), "module initialization failed");
  codeOffset += Align(size, DK_SHADER_CODE_ALIGNMENT);
}
void Initialize() {
  Log("stage=device");
  DkDeviceMaker dm;
  dkDeviceMakerDefaults(&dm);
  dm.flags = DkDeviceFlags_OriginUpperLeft | DkDeviceFlags_DepthZeroToOne;
  dm.cbDebug = Debug;
  device = dkDeviceCreate(&dm);
  Check(device != nullptr, "device creation failed");
  unsigned requiredScratch = 0;
  for (size_t i = 0; i < kModuleCount; ++i) {
    std::string path =
        std::string("sdmc:/switch/retuned-deko-probe/modules/") + kModules[i];
    FILE *f = fopen(path.c_str(), "rb");
    Check(f != nullptr, "module file missing during requirements scan");
    unsigned header[6], program[6];
    bool ok = fread(header, sizeof(header), 1, f) == 1;
    ok = ok && header[0] == 0x48534b44 && header[5] == 1 && header[4] >= 24 &&
         header[4] <= 1024 * 1024;
    ok = ok && fseek(f, header[4], SEEK_SET) == 0 &&
         fread(program, sizeof(program), 1, f) == 1;
    fclose(f);
    Check(ok, "module requirements header invalid");
    Check(program[5] <= 65536,
          "module scratch requirement exceeds probe limit");
    if (program[5] > requiredScratch)
      requiredScratch = program[5];
  }
  Log("stage=queue");
  DkQueueMaker qm;
  dkQueueMakerDefaults(&qm, device);
  qm.flags = DkQueueFlags_Graphics;
  if (requiredScratch > qm.perWarpScratchMemorySize)
    qm.perWarpScratchMemorySize =
        Align(requiredScratch, DK_PER_WARP_SCRATCH_MEM_ALIGNMENT);
  fprintf(logFile, "queue_scratch_per_warp=%u required=%u\n",
          qm.perWarpScratchMemorySize, requiredScratch);
  queue = dkQueueCreate(&qm);
  Check(queue != nullptr, "queue creation failed");
  codeMem =
      Memory(CodeSize, DkMemBlockFlags_CpuUncached | DkMemBlockFlags_GpuCached |
                           DkMemBlockFlags_Code);
  cmdMem =
      Memory(CmdSize, DkMemBlockFlags_CpuUncached | DkMemBlockFlags_GpuCached);
  dataMem = Memory(1024 * 1024, DkMemBlockFlags_CpuUncached |
                                    DkMemBlockFlags_GpuCached |
                                    DkMemBlockFlags_ZeroFillInit);
  DkCmdBufMaker cm;
  dkCmdBufMakerDefaults(&cm, device);
  cmd = dkCmdBufCreate(&cm);
  Check(cmd != nullptr, "command buffer failed");
  dkCmdBufAddMemory(cmd, cmdMem, 0, CmdSize);
  Log("stage=framebuffer");
  DkImageLayoutMaker lm;
  dkImageLayoutMakerDefaults(&lm, device);
  lm.flags = DkImageFlags_UsageRender;
  lm.format = DkImageFormat_RGBA8_Unorm;
  lm.dimensions[0] = W;
  lm.dimensions[1] = H;
  DkImageLayout layout;
  dkImageLayoutInitialize(&layout, &lm);
  frameSize =
      Align(dkImageLayoutGetSize(&layout), dkImageLayoutGetAlignment(&layout));
  imageMem =
      Memory(2 * frameSize, DkMemBlockFlags_GpuCached | DkMemBlockFlags_Image);
  const DkImage *images[2];
  for (unsigned i = 0; i < 2; i++) {
    dkImageInitialize(&frames[i], &layout, imageMem, i * frameSize);
    images[i] = &frames[i];
  }

  Log("stage=empty-submit");
  Submit();
  Log("stage=modules");
  shaders.resize(kModuleCount);
  for (size_t i = 0; i < kModuleCount; i++) {
    fprintf(logFile, "module=%zu\n", i);
    fflush(logFile);
    LoadModule(i);
  }
  fprintf(logFile, "modules_initialized=%zu\n", shaders.size());
  fflush(logFile);
  Log("stage=texture");
  lm.flags = 0;
  lm.dimensions[0] = 1;
  lm.dimensions[1] = 1;
  lm.format = DkImageFormat_RGBA8_Unorm;
  DkImageLayout tl;
  dkImageLayoutInitialize(&tl, &lm);
  unsigned ts =
      Align(dkImageLayoutGetSize(&tl), dkImageLayoutGetAlignment(&tl));
  lm.format = DkImageFormat_R32_Uint;
  DkImageLayout il;
  dkImageLayoutInitialize(&il, &lm);
  unsigned ti = Align(ts, dkImageLayoutGetAlignment(&il));
  textureMem = Memory(ti + dkImageLayoutGetSize(&il),
                      DkMemBlockFlags_GpuCached | DkMemBlockFlags_Image);
  dkImageInitialize(&texture, &tl, textureMem, 0);
  dkImageInitialize(&integerTexture, &il, textureMem, ti);
  auto *data = static_cast<unsigned char *>(dkMemBlockGetCpuAddr(dataMem));
  memset(data, 0, 1024 * 1024);
  data[TextureOffset] = 64;
  data[TextureOffset + 1] = 128;
  data[TextureOffset + 2] = 192;
  data[TextureOffset + 3] = 255;
  DkImageView tv;
  dkImageViewDefaults(&tv, &texture);
  DkCopyBuf input{dkMemBlockGetGpuAddr(dataMem) + TextureOffset, 0, 0};
  DkImageRect rect{0, 0, 0, 1, 1, 1};
  dkCmdBufCopyBufferToImage(cmd, &input, &tv, &rect, 0);
  DkImageView iv;
  dkImageViewDefaults(&iv, &integerTexture);
  DkCopyBuf zero{dkMemBlockGetGpuAddr(dataMem) + TextureOffset + 256, 0, 0};
  dkCmdBufCopyBufferToImage(cmd, &zero, &iv, &rect, 0);
  dkCmdBufBarrier(cmd, DkBarrier_Full,
                  DkInvalidateFlags_Image | DkInvalidateFlags_Descriptors |
                      DkInvalidateFlags_Shader);
  Submit();
  auto *descriptors =
      reinterpret_cast<DkImageDescriptor *>(data + ImageDescriptorOffset);
  dkImageDescriptorInitialize(&descriptors[0], &tv, false, false);
  dkImageDescriptorInitialize(&descriptors[1], &iv, false, false);
  DkSampler sampler;
  dkSamplerDefaults(&sampler);
  sampler.minFilter = DkFilter_Nearest;
  sampler.magFilter = DkFilter_Nearest;
  dkSamplerDescriptorInitialize(
      reinterpret_cast<DkSamplerDescriptor *>(data + SamplerDescriptorOffset),
      &sampler);
}
void Test(const ProbeTest &test) {
#ifdef RETUNED_PROBE_UNIFORM_FIXTURES
  auto *uniforms = static_cast<unsigned char *>(dkMemBlockGetCpuAddr(dataMem));
  memset(uniforms + UniformOffset, 0, 16384);
  for (size_t i = 0; i < test.uniformCount; ++i) {
    Check(test.uniforms[i].offset <= 16384 - sizeof(unsigned),
          "uniform write out of bounds");
    memcpy(uniforms + UniformOffset + test.uniforms[i].offset,
           &test.uniforms[i].value, sizeof(unsigned));
  }
#endif
  fprintf(logFile, "stage=test %s\n", test.name);
  fflush(logFile);
  int slot = 0;
  DkImageView view;
  dkImageViewDefaults(&view, &frames[slot]);
  dkCmdBufBindRenderTarget(cmd, &view, nullptr);
  DkViewport viewport{0, 0, float(W), float(H), 0, 1};
  DkScissor scissor{0, 0, W, H};
  // Restrict the semantic probe independently of shader compilation.
  if (test.mode != 3) {
    const unsigned extent = RETUNED_PROBE_PIXEL_EXTENT;
    scissor = {int(W / 2 - extent / 2), int(H / 2 - extent / 2), extent,
               extent};
  }
  dkCmdBufSetViewports(cmd, 0, &viewport, 1);
  dkCmdBufSetScissors(cmd, 0, &scissor, 1);
  DkRasterizerState raster;
  dkRasterizerStateDefaults(&raster);
  raster.cullMode = DkFace_None;
  dkCmdBufBindRasterizerState(cmd, &raster);
  DkColorState color;
  dkColorStateDefaults(&color);
  dkCmdBufBindColorState(cmd, &color);
  DkColorWriteState writes;
  dkColorWriteStateDefaults(&writes);
  dkCmdBufBindColorWriteState(cmd, &writes);
  DkDepthStencilState depth;
  dkDepthStencilStateDefaults(&depth);
  depth.depthTestEnable = false;
  depth.depthWriteEnable = false;
  dkCmdBufBindDepthStencilState(cmd, &depth);
  dkCmdBufClearColorFloat(cmd, 0, DkColorMask_RGBA, 1, 0, 1, 1);
  const DkShader *pair[2] = {&shaders[kControlVertex], &shaders[test.fragment]};
  dkCmdBufBindShaders(cmd, DkStageFlag_GraphicsMask, pair, 2);
  dkCmdBufBindUniformBuffer(cmd, DkStage_Fragment, 0,
                            dkMemBlockGetGpuAddr(dataMem) + UniformOffset,
                            16384);
  dkCmdBufBindImageDescriptorSet(
      cmd, dkMemBlockGetGpuAddr(dataMem) + ImageDescriptorOffset, 2);
  dkCmdBufBindSamplerDescriptorSet(
      cmd, dkMemBlockGetGpuAddr(dataMem) + SamplerDescriptorOffset, 1);
  DkResHandle handles[4];
  for (unsigned i = 0; i < 4; i++)
    handles[i] = dkMakeTextureHandle(test.integer0 && i == 0 ? 1 : 0, 0);
  dkCmdBufBindTextures(cmd, DkStage_Fragment, 0, handles, 4);
  dkCmdBufDraw(cmd, DkPrimitive_Triangles, 3, 1, 0, 0);
  dkCmdBufBarrier(cmd, DkBarrier_Full, DkInvalidateFlags_L2Cache);
  DkImageRect rect{0, 0, 0, W, H, 1};
  DkCopyBuf output{dkMemBlockGetGpuAddr(dataMem) + ReadbackOffset, 0, 0};
  dkCmdBufCopyImageToBuffer(cmd, &view, &rect, &output, 0);
  Submit();
  auto *pixel = static_cast<unsigned char *>(dkMemBlockGetCpuAddr(dataMem)) +
                ReadbackOffset;
  unsigned mismatches = 0;
  if (test.mode == 3) {
    for (unsigned y = 0; y < 2; y++)
      for (unsigned x = 0; x < 64; x++) {
        int n = kMathValues[x];
        int result = y == 0 ? n / 9 : (n / 2) % 2;
        uint32_t value = uint32_t(result);
        auto *p = pixel + (y * W + x) * 4;
        for (unsigned c = 0; c < 4; c++)
          if (p[c] != ((value >> (8 * c)) & 255))
            mismatches++;
      }
  } else {
    auto *p = pixel + (H / 2 * W + W / 2) * 4;
    const unsigned char expected[3][4] = {
        {255, 0, 0, 255}, {255, 255, 255, 255}, {64, 128, 192, 255}};
    const unsigned char *wanted = expected[test.mode < 3 ? test.mode : 0];
#ifdef RETUNED_PROBE_UNIFORM_FIXTURES
    if (test.mode == 4)
      wanted = test.expected;
#endif
    for (unsigned y = unsigned(scissor.y);
         y < unsigned(scissor.y) + scissor.height; ++y)
      for (unsigned x = unsigned(scissor.x);
           x < unsigned(scissor.x) + scissor.width; ++x)
        for (unsigned c = 0; c < 4; ++c)
          if (abs(int(pixel[(y * W + x) * 4 + c]) - wanted[c]) > 1)
            ++mismatches;
    fprintf(logFile, "checked_pixels=%u\n", scissor.width * scissor.height);
    fprintf(logFile, "pixel=%u,%u,%u,%u\n", p[0], p[1], p[2], p[3]);
  }
  fprintf(logFile, "result=%s mismatches=%u name=%s\n",
          mismatches ? "FAIL" : "PASS", mismatches, test.name);
  fflush(logFile);
  Check(mismatches == 0, "pixel comparison failed");
}
} // namespace
int main() {
  mkdir("sdmc:/switch", 0777);
  mkdir("sdmc:/switch/retuned-deko-probe", 0777);
  logFile = fopen("sdmc:/switch/retuned-deko-probe/result.txt", "w");
  if (!logFile)
    return 2;
  setvbuf(logFile, nullptr, _IONBF, 0);
  Log("status=RUNNING");
  try {
    Initialize();
    for (const auto &t : kTests)
      if (t.mode == 3)
        Test(t);
    for (const auto &t : kTests)
      if (t.mode != 3)
        Test(t);
    Log("status=PASS");
    Log("scope=module initialization and selected fragment/readback cases "
        "only; original PICA vertex semantics and full gameplay not validated");
    for (unsigned i = 0; i < 300 && appletMainLoop(); i++)
      svcSleepThread(16'666'667);
    return 0;
  } catch (const std::exception &e) {
    fprintf(logFile, "status=FAIL\nerror=%s\n", e.what());
    fflush(logFile);
    for (unsigned i = 0; i < 60 && appletMainLoop(); i++)
      svcSleepThread(16'666'667);
    return 1;
  }
}
