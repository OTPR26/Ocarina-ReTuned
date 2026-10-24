// SPDX-License-Identifier: GPL-2.0-or-later
#include "backend.h"
#include "gpu.h"
#include "scissor.h"
#include "texture_policy.h"
#include "oot3d/renderer/azahar_texture_pack.h"
#include "fast/oot3d/graphics_settings_runtime.h"
#include "native_coordinates.h"
#include "imgui.h"
#include "fast/renderer3ds/pica_composition_schedule.h"
#include "oot3d/renderer/pica_texture_decode.h"
#include "fast/oot3d/pica_shadow2d.h"
#include <array>
#include <algorithm>
#include <map>
#include <tuple>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <stdexcept>
namespace Fast {
namespace {
using RetunedDeko::Gpu;using RetunedDeko::Image;
GfxRenderingAPIDeko* active=nullptr;
void Require(bool b,const char*message){if(!b)throw std::runtime_error(message);}
DkCompareOp Compare(GfxNativePicaCompareFunction v){static constexpr DkCompareOp values[]={DkCompareOp_Never,DkCompareOp_Always,DkCompareOp_Equal,DkCompareOp_NotEqual,DkCompareOp_Less,DkCompareOp_Lequal,DkCompareOp_Greater,DkCompareOp_Gequal};return values[unsigned(v)&7];}
const char* UiVertex=R"(#version 450
layout(location=0) in vec2 position;
layout(location=1) in vec2 uv;
layout(location=2) in vec4 color;
layout(location=0) out vec2 v_uv;
layout(location=1) out vec4 v_color;
layout(set=0,binding=0,std140) uniform Gui {vec4 transform;} gui;
void main(){gl_Position=vec4(position*gui.transform.xy+gui.transform.zw,0,1);v_uv=uv;v_color=color;}
)";
const char* UiFragment=R"(#version 450
layout(location=0) in vec2 v_uv;
layout(location=1) in vec4 v_color;
layout(set=0,binding=0) uniform sampler2D image;
layout(location=0) out vec4 output_color;
void main(){output_color=v_color*texture(image,v_uv);}
)";
const char* ScanVertex=R"(#version 450
layout(location=0) out vec2 uv;
void main(){vec2 p[3]=vec2[3](vec2(-1,-1),vec2(3,-1),vec2(-1,3));gl_Position=vec4(p[gl_VertexID],0,1);uv=p[gl_VertexID]*0.5+0.5;}
)";
const char* ScanFragment=R"(#version 450
layout(location=0) in vec2 uv;
layout(set=0,binding=0) uniform sampler2D image;
layout(location=0) out vec4 output_color;
void main(){output_color=texture(image,vec2(uv.y,uv.x));}
)";
void Raster(Gpu&g,bool blend=false){DkRasterizerState r;dkRasterizerStateDefaults(&r);r.cullMode=DkFace_None;dkCmdBufBindRasterizerState(g.cmd,&r);DkDepthStencilState d;dkDepthStencilStateDefaults(&d);d.depthTestEnable=false;d.depthWriteEnable=false;dkCmdBufBindDepthStencilState(g.cmd,&d);DkColorState c;dkColorStateDefaults(&c);dkColorStateSetBlendEnable(&c,0,blend);dkCmdBufBindColorState(g.cmd,&c);DkColorWriteState w;dkColorWriteStateDefaults(&w);dkCmdBufBindColorWriteState(g.cmd,&w);if(blend){DkBlendState b;dkBlendStateDefaults(&b);dkBlendStateSetFactors(&b,DkBlendFactor_SrcAlpha,DkBlendFactor_InvSrcAlpha,DkBlendFactor_One,DkBlendFactor_InvSrcAlpha);dkCmdBufBindBlendState(g.cmd,0,&b);}}
uint64_t Hash(std::span<const uint8_t>b){uint64_t h=1469598103934665603ULL;for(auto n:b)h=(h^n)*1099511628211ULL;return h;}
uint32_t PicaColorBytesPerPixel(uint8_t format) {
    return format == 0U ? 4U : (format == 1U ? 3U : 2U);
}

uint32_t PicaDepthBytesPerPixel(uint8_t format) {
    return format == 0U ? 2U : (format == 2U ? 3U : 4U);
}

uint32_t PicaFillElementSize(uint16_t control) {
    return (control & (1U << 9U)) != 0U
        ? 4U
        : ((control & (1U << 8U)) != 0U ? 3U : 2U);
}

uint8_t PicaFillByte(const GfxNativePicaMemoryFillView& fill,
                     uint32_t index) {
    const uint32_t shift =
        (index % PicaFillElementSize(fill.Control)) * 8U;
    return static_cast<uint8_t>(fill.Value >> shift);
}

float PicaUnorm(uint32_t value, uint32_t maximum) {
    return static_cast<float>(value) / static_cast<float>(maximum);
}

std::array<float, 4> DecodePicaClearColor(
    const GfxNativePicaMemoryFillView& fill, uint8_t format) {
    const uint8_t b0 = PicaFillByte(fill, 0U);
    const uint8_t b1 = PicaFillByte(fill, 1U);
    const uint8_t b2 = PicaFillByte(fill, 2U);
    const uint8_t b3 = PicaFillByte(fill, 3U);
    if (format == 0U) {
        return {PicaUnorm(b3, 0xFFU), PicaUnorm(b2, 0xFFU),
                PicaUnorm(b1, 0xFFU), PicaUnorm(b0, 0xFFU)};
    }
    if (format == 1U) {
        return {PicaUnorm(b2, 0xFFU), PicaUnorm(b1, 0xFFU),
                PicaUnorm(b0, 0xFFU), 1.0F};
    }
    const uint16_t packed = static_cast<uint16_t>(b0) |
                            static_cast<uint16_t>(b1) << 8U;
    if (format == 2U) {
        return {PicaUnorm((packed >> 11U) & 0x1FU, 0x1FU),
                PicaUnorm((packed >> 5U) & 0x3FU, 0x3FU),
                PicaUnorm(packed & 0x1FU, 0x1FU), 1.0F};
    }
    if (format == 3U) {
        return {PicaUnorm((packed >> 11U) & 0x1FU, 0x1FU),
                PicaUnorm((packed >> 6U) & 0x1FU, 0x1FU),
                PicaUnorm((packed >> 1U) & 0x1FU, 0x1FU),
                static_cast<float>(packed & 1U)};
    }
    return {PicaUnorm((packed >> 12U) & 0xFU, 0xFU),
            PicaUnorm((packed >> 8U) & 0xFU, 0xFU),
            PicaUnorm((packed >> 4U) & 0xFU, 0xFU),
            PicaUnorm(packed & 0xFU, 0xFU)};
}

std::pair<float, uint8_t> DecodePicaClearDepthStencil(
    const GfxNativePicaMemoryFillView& fill, uint8_t format) {
    const uint32_t b0 = PicaFillByte(fill, 0U);
    const uint32_t b1 = PicaFillByte(fill, 1U);
    const uint32_t b2 = PicaFillByte(fill, 2U);
    const uint32_t depth = format == 0U
        ? b0 | (b1 << 8U)
        : b0 | (b1 << 8U) | (b2 << 16U);
    return {PicaUnorm(depth, format == 0U ? 0xFFFFU : 0xFFFFFFU),
            format == 3U ? PicaFillByte(fill, 3U) : 0U};
}

struct Target {std::unique_ptr<Image> color,depth,shadow;};
using TargetKey=std::tuple<uint64_t,uint32_t,uint32_t,uint16_t,uint16_t,uint8_t,uint8_t>;
}
struct GfxRenderingAPIDeko::Impl {
 struct NativeTexture {
  std::unique_ptr<Image> image;
  uint64_t used=0,generation=0,hash=0,polled=0;
  bool hashAvailable=false,replaced=false;
  ::Oot3d::Renderer::AzaharTextureResolveState resolve=::Oot3d::Renderer::AzaharTextureResolveState::Pending;
 };
 uint64_t textureFrame=0,textureBytes=0,replacementUploads=0,textureGeneration=0;
 bool texturePressure=false,customTexturesEnabled=false;
 uint64_t textureSettingsRevision=~0ULL;

 std::unique_ptr<Image> fallbackColor,fallbackInteger;
 std::unique_ptr<Gpu> gpu;std::map<unsigned,std::unique_ptr<Image>> textures;unsigned nextTexture=1,selectedTexture=0,currentFb=0,font=0;FilteringMode filter=FILTER_LINEAR;
 std::map<int,Target> framebuffers;int nextFb=1;
 std::map<TargetKey,Target> targets;std::map<std::tuple<uint64_t,uint32_t,unsigned,unsigned,unsigned>,NativeTexture> nativeTextures;
 std::map<uint64_t,std::unique_ptr<Image>> lighting;
 std::vector<GfxNativePicaMemoryFillView> fills;std::vector<uint64_t> completions;Renderer3ds::PicaCompositionSchedule composition;
 Target& Surface(const GfxNativePicaDrawView&d){TargetKey k{d.RenderTargetNamespace,d.FramebufferColorPhysicalAddress,d.FramebufferDepthPhysicalAddress,d.FramebufferWidth,d.FramebufferHeight,d.FramebufferColorFormat,d.FramebufferDepthFormat};auto&t=targets[k];if(!t.color){t.color=gpu->Create(d.FramebufferWidth*3,d.FramebufferHeight*3,DkImageFormat_RGBA8_Unorm);t.depth=gpu->Create(d.FramebufferWidth*3,d.FramebufferHeight*3,DkImageFormat_Z24S8);t.shadow=gpu->Create(d.FramebufferWidth,d.FramebufferHeight,DkImageFormat_R32_Uint,false,true);gpu->Bind(*t.color,t.depth.get());dkCmdBufClearColorFloat(gpu->cmd,0,DkColorMask_RGBA,0,0,0,0);dkCmdBufClearDepthStencil(gpu->cmd,true,1,255,0);}ApplyFills(k,t);return t;}
 void ApplyFills(const TargetKey&k,Target&t){
  for(auto i=fills.begin();i!=fills.end();){
   auto&f=*i;if(f.RenderTargetNamespace!=std::get<0>(k)){++i;continue;}
   uint64_t count=uint64_t(std::get<3>(k))*std::get<4>(k);
   auto colorAddress=std::get<1>(k),depthAddress=std::get<2>(k);
   bool color=f.StartPhysicalAddress<=colorAddress&&f.EndPhysicalAddress>=colorAddress+count*PicaColorBytesPerPixel(std::get<5>(k));
   bool depth=depthAddress&&f.StartPhysicalAddress<=depthAddress&&f.EndPhysicalAddress>=depthAddress+count*PicaDepthBytesPerPixel(std::get<6>(k));
   if(!color&&!depth){++i;continue;}gpu->Bind(*t.color,t.depth.get());
   if(color){gpu->Bind(*t.shadow);unsigned packed=f.Value;dkCmdBufClearColor(gpu->cmd,0,DkColorMask_R,&packed);gpu->Bind(*t.color,t.depth.get());auto v=DecodePicaClearColor(f,std::get<5>(k));dkCmdBufClearColorFloat(gpu->cmd,0,DkColorMask_RGBA,v[0],v[1],v[2],v[3]);}
   if(depth){auto v=DecodePicaClearDepthStencil(f,std::get<6>(k));dkCmdBufClearDepthStencil(gpu->cmd,true,v.first,255,v.second);}
   i=fills.erase(i);
  }
 }
 void BeginTextures() {
  ++textureFrame;replacementUploads=0;
  auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();
  auto snapshot=Oot3d::GraphicsSettingsRuntime::Instance().SnapshotWithRevision();
  if(snapshot.Revision!=textureSettingsRevision) {
   const auto& settings=snapshot.Value.TexturePacks.Azahar;
   customTexturesEnabled=settings.LoadCustomTextures;
   packs.Configure({.DumpTextures=false,.LoadCustomTextures=settings.LoadCustomTextures,
     .LoadDirectory=settings.LoadDirectory.empty()?"sdmc:/switch/oot3dre/textures":settings.LoadDirectory});
   textureSettingsRevision=snapshot.Revision;
  }
  const auto generation=packs.Generation();
  if(generation!=textureGeneration) {
   // Present fenced the previous frame; no pending draw may reference these.
   nativeTextures.clear();textureBytes=0;textureGeneration=generation;
  }
  const uint64_t target=texturePressure?RetunedDeko::TextureGpuBudget*3/4:RetunedDeko::TextureGpuBudget;
  while(!nativeTextures.empty()&&(textureBytes>target||nativeTextures.size()>RetunedDeko::TextureRecordBudget)) {
   auto oldest=std::min_element(nativeTextures.begin(),nativeTextures.end(),[](const auto&a,const auto&b){return a.second.used<b.second.used;});
   textureBytes-=oldest->second.image?oldest->second.image->allocatedBytes:0;
   nativeTextures.erase(oldest);
  }
  texturePressure=false;
 }
 Image& Texture(const GfxNativePicaTextureView&t) {
  auto hashStart=gpu->BeginWork();
  auto contentHash=t.NativeContentHashAvailable?t.NativeContentHash:Hash(t.NativeBytes);
  gpu->EndWork("texture-hash",hashStart);
  auto key=std::make_tuple(contentHash,t.PhysicalAddress,unsigned(t.Width),unsigned(t.Height),unsigned(t.NativeFormat)|unsigned(t.NativeType)<<8);
  auto& record=nativeTextures[key];record.used=textureFrame;
  Require(t.CopyReferences.empty(),"deko GPU texture-copy sampling not implemented");
  if(record.replaced)return *record.image;
  std::vector<uint8_t> pixels;std::string error;
  if(customTexturesEnabled&&t.NativeType!=2&&record.polled!=textureFrame) {
   record.polled=textureFrame;
   auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();
   ::Oot3d::Renderer::AzaharTextureResolveResult result;
   if(record.hashAvailable) result=packs.PollQueued(record.hash);
   else if(auto size=RetunedDeko::NativeTextureBaseBytes(t.NativeFormat,t.Width,t.Height);size&&*size<=t.NativeBytes.size()) {
    // Legacy Citra packs hash decoded RGBA for intensity/compressed formats.
    // Supplying only encoded bytes silently misses those replacements.
    if(t.NativeFormat>=5)Require(::Oot3d::Renderer::DecodePicaTextureRgba8(t.NativeFormat,t.Width,t.Height,t.NativeBytes,pixels,&error),error.c_str());
    result=packs.ResolveOrQueue({t.Width,t.Height,t.NativeFormat,0,t.NativeBytes.first(*size),pixels});
    record.hash=result.NativeHash;record.hashAvailable=result.NativeHashAvailable;
   }
   record.resolve=result.State;
   if(result.State==::Oot3d::Renderer::AzaharTextureResolveState::Ready&&result.Replacement&&result.Replacement->Rgba8) {
    const auto& replacement=*result.Replacement;const auto bytes=replacement.Rgba8->size();
    if(RetunedDeko::ReplacementFits(replacement.Width,replacement.Height,bytes,textureBytes,replacementUploads)) {
     auto image=gpu->Create(replacement.Width,replacement.Height,DkImageFormat_RGBA8_Unorm);
     gpu->UploadImage(*image,*replacement.Rgba8);
     // Replacing an image must wait for prior draws referencing its descriptor.
     if(record.image){gpu->Submit(false,"texture-promotion");textureBytes-=record.image->allocatedBytes;}
     textureBytes+=image->allocatedBytes;record.image=std::move(image);record.replaced=true;
     replacementUploads+=bytes;
     std::printf("deko custom texture hash=%016llx native=%ux%u replacement=%ux%u gpu_bytes=%llu\n",(unsigned long long)record.hash,t.Width,t.Height,replacement.Width,replacement.Height,(unsigned long long)textureBytes);
     return *record.image;
    }
    texturePressure=true;
   }
  }
  if(record.image)return *record.image;
  if(t.NativeType==2){std::vector<uint32_t> p;Require(Oot3d::DetilePicaShadow2d(t.NativeBytes,t.Width,t.Height,p,&error),error.c_str());pixels.resize(p.size()*4);memcpy(pixels.data(),p.data(),pixels.size());record.image=gpu->Create(t.Width,t.Height,DkImageFormat_R32_Uint);}
  else{if(pixels.empty())Require(::Oot3d::Renderer::DecodePicaTextureRgba8(t.NativeFormat,t.Width,t.Height,t.NativeBytes,pixels,&error),error.c_str());record.image=gpu->Create(t.Width,t.Height,DkImageFormat_RGBA8_Unorm);}
  gpu->UploadImage(*record.image,pixels);textureBytes+=record.image->allocatedBytes;
  if(textureBytes>RetunedDeko::TextureGpuBudget||nativeTextures.size()>RetunedDeko::TextureRecordBudget)texturePressure=true;
  return *record.image;
 }

};
GfxRenderingAPIDeko::GfxRenderingAPIDeko():state(std::make_unique<Impl>()){active=this;}
GfxRenderingAPIDeko::~GfxRenderingAPIDeko(){Shutdown();}
const char* GfxRenderingAPIDeko::GetName(){return "deko3d (experimental)";}
int GfxRenderingAPIDeko::GetMaxTextureSize(){return 8192;}
GfxClipParameters GfxRenderingAPIDeko::GetClipParameters(){return {true,false};}
void GfxRenderingAPIDeko::Init(){if(!state->gpu)state->gpu=std::make_unique<Gpu>();active=this;}
void GfxRenderingAPIDeko::Shutdown(){if(active==this)active=nullptr;if(state->gpu)state->gpu->Submit();state->textures.clear();state->targets.clear();state->nativeTextures.clear();state->framebuffers.clear();state->lighting.clear();state->fallbackColor.reset();state->fallbackInteger.reset();state->gpu.reset();}
void GfxRenderingAPIDeko::OnResize(){}
void GfxRenderingAPIDeko::StartFrame(){auto&g=*state->gpu;g.BeginProfileFrame();state->BeginTextures();g.Bind(g.Screen());dkCmdBufClearColorFloat(g.cmd,0,DkColorMask_RGBA,mClearColor[0],mClearColor[1],mClearColor[2],mClearColor[3]);}
void GfxRenderingAPIDeko::EndFrame(){}
void GfxRenderingAPIDeko::FinishRender(){}
void GfxRenderingAPIDeko::Present(){state->gpu->Present();}
void GfxRenderingAPIDeko::SetTextureFilter(FilteringMode m){state->filter=m;}
FilteringMode GfxRenderingAPIDeko::GetTextureFilter(){return state->filter;}
uint32_t GfxRenderingAPIDeko::NewTexture(){return state->nextTexture++;}
void GfxRenderingAPIDeko::SelectTexture(int,uint32_t id){state->selectedTexture=id;}
void GfxRenderingAPIDeko::UploadTexture(const uint8_t*bytes,uint32_t w,uint32_t h){auto&g=*state->gpu;g.Submit(false,"ui-texture");auto&i=state->textures[state->selectedTexture];if(!i||i->width!=w||i->height!=h)i=g.Create(w,h,DkImageFormat_RGBA8_Unorm);g.UploadImage(*i,{bytes,size_t(w)*h*4});}
void GfxRenderingAPIDeko::DeleteTexture(uint32_t id){state->gpu->Submit();state->textures.erase(id);}
ImTextureID GfxRenderingAPIDeko::GetTextureById(int id){return reinterpret_cast<ImTextureID>(uintptr_t(id));}
void GfxRenderingAPIDeko::SetSamplerParameters(int,bool,uint32_t,uint32_t){}
void GfxRenderingAPIDeko::SetSrgbMode(){}
int GfxRenderingAPIDeko::CreateFramebuffer(){int id=state->nextFb++;state->framebuffers[id];return id;}
void GfxRenderingAPIDeko::UpdateFramebufferParameters(int id,uint32_t w,uint32_t h,uint32_t msaa,bool,bool,bool depth,bool){Require(msaa<=1,"deko MSAA framebuffer not implemented");auto&g=*state->gpu;auto&t=state->framebuffers[id];if(t.color&&t.color->width==w&&t.color->height==h&&bool(t.depth)==depth)return;g.Submit(false,"framebuffer-resize");t.color=g.Create(w,h,DkImageFormat_RGBA8_Unorm);t.depth.reset();if(depth)t.depth=g.Create(w,h,DkImageFormat_Z24S8);}
void GfxRenderingAPIDeko::StartDrawToFramebuffer(int id,float){state->currentFb=id;auto&g=*state->gpu;if(!id)g.Bind(g.Screen());else{auto&t=state->framebuffers.at(id);Require(bool(t.color),"deko framebuffer not allocated");g.Bind(*t.color,t.depth.get());}}
void GfxRenderingAPIDeko::ClearFramebuffer(bool color,bool depth){auto&g=*state->gpu;if(color)dkCmdBufClearColorFloat(g.cmd,0,DkColorMask_RGBA,mClearColor[0],mClearColor[1],mClearColor[2],mClearColor[3]);if(depth)dkCmdBufClearDepthStencil(g.cmd,true,1,255,0);}
void* GfxRenderingAPIDeko::GetFramebufferTextureId(int id){return reinterpret_cast<void*>(uintptr_t(0x40000000u|unsigned(id)));}
void GfxRenderingAPIDeko::GuiInit(){Init();auto&io=ImGui::GetIO();unsigned char*data;int w,h;io.Fonts->GetTexDataAsRGBA32(&data,&w,&h);state->font=NewTexture();SelectTexture(0,state->font);UploadTexture(data,w,h);io.Fonts->SetTexID(reinterpret_cast<ImTextureID>(uintptr_t(state->font)));io.BackendRendererName="Ocarina ReTuned deko3d";io.BackendFlags|=ImGuiBackendFlags_RendererHasVtxOffset;}
void GfxRenderingAPIDeko::GuiRender(ImDrawData*data){if(!data||data->DisplaySize.x<=0||data->DisplaySize.y<=0)return;auto&g=*state->gpu;g.Bind(g.Screen());Raster(g,true);auto&vs=g.shaders->Get(DkStage_Vertex,UiVertex);auto&fs=g.shaders->Get(DkStage_Fragment,UiFragment);const DkShader*pair[]={&vs.shader,&fs.shader};dkCmdBufBindShaders(g.cmd,DkStageFlag_GraphicsMask,pair,2);float transform[]={2/data->DisplaySize.x,-2/data->DisplaySize.y,-1-data->DisplayPos.x*2/data->DisplaySize.x,1+data->DisplayPos.y*2/data->DisplaySize.y};auto ub=g.Upload({reinterpret_cast<unsigned char*>(transform),sizeof(transform)});dkCmdBufBindUniformBuffer(g.cmd,DkStage_Vertex,0,ub,256);DkVtxAttribState a[3]{};a[0].offset=offsetof(ImDrawVert,pos);a[0].size=DkVtxAttribSize_2x32;a[0].type=DkVtxAttribType_Float;a[1].offset=offsetof(ImDrawVert,uv);a[1].size=DkVtxAttribSize_2x32;a[1].type=DkVtxAttribType_Float;a[2].offset=offsetof(ImDrawVert,col);a[2].size=DkVtxAttribSize_4x8;a[2].type=DkVtxAttribType_Unorm;dkCmdBufBindVtxAttribState(g.cmd,a,3);DkVtxBufferState b{sizeof(ImDrawVert),0};dkCmdBufBindVtxBufferState(g.cmd,&b,1);
 for(int n=0;n<data->CmdListsCount;n++){auto*l=data->CmdLists[n];auto vb=g.Upload({reinterpret_cast<const unsigned char*>(l->VtxBuffer.Data),size_t(l->VtxBuffer.Size)*sizeof(ImDrawVert)});auto ib=g.Upload({reinterpret_cast<const unsigned char*>(l->IdxBuffer.Data),size_t(l->IdxBuffer.Size)*sizeof(ImDrawIdx)});DkBufExtents extent{vb,size_t(l->VtxBuffer.Size)*sizeof(ImDrawVert)};dkCmdBufBindVtxBuffers(g.cmd,0,&extent,1);dkCmdBufBindIdxBuffer(g.cmd,sizeof(ImDrawIdx)==2?DkIdxFormat_Uint16:DkIdxFormat_Uint32,ib);
 for(const auto&c:l->CmdBuffer){if(c.UserCallback){if(c.UserCallback!=ImDrawCallback_ResetRenderState)c.UserCallback(l,&c);continue;}unsigned id=unsigned(reinterpret_cast<uintptr_t>(c.GetTexID()));Image*image=nullptr;if(id&0x40000000u){unsigned fb=id&~0x40000000u;image=fb?state->framebuffers.at(fb).color.get():&g.Screen();}else{auto found=state->textures.find(id);if(found!=state->textures.end())image=found->second.get();}Require(image,"deko ImGui texture missing");g.BindTexture(DkStage_Fragment,0,*image);const auto clip=RetunedDeko::GuiClip(g.Screen().width,g.Screen().height,
 data->DisplayPos.x,data->DisplayPos.y,data->DisplaySize.x,data->DisplaySize.y,
 c.ClipRect.x,c.ClipRect.y,c.ClipRect.z,c.ClipRect.w);
 if(!clip.width||!clip.height)continue;
 DkScissor sc{clip.x,clip.y,unsigned(clip.width),unsigned(clip.height)};dkCmdBufSetScissors(g.cmd,0,&sc,1);dkCmdBufDrawIndexed(g.cmd,DkPrimitive_Triangles,c.ElemCount,1,c.IdxOffset,c.VtxOffset,0);}
 }g.Submit(true,"gui");}
bool GfxRenderingAPIDeko::PublishPicaCompositionSequence(const Renderer3ds::PicaCompositionSequenceView&s,std::string*error){return state->composition.Compile(s,error);}
bool GfxRenderingAPIDeko::SubmitPicaDraw(const GfxNativePicaDrawView&d,std::string*error){try{auto&g=*state->gpu;Require(!d.VertexShaderSource.empty()&&!d.FragmentShaderSource.empty(),"deko draw shader missing");if(state->composition.Valid())Require(state->composition.ConsumeDraw(Renderer3ds::BuildPicaCompositionDrawReference(d),error),"deko composition order mismatch");auto drawStart=g.BeginWork();auto shaderStart=g.BeginWork();auto&vs=g.shaders->Get(DkStage_Vertex,std::string(d.VertexShaderSource));auto&fs=g.shaders->Get(DkStage_Fragment,std::string(d.FragmentShaderSource));g.EndWork("shader-lookup",shaderStart);auto&t=state->Surface(d);g.Bind(*t.color,t.depth.get());Raster(g,d.Blend.Enabled);
 DkBlendState blend;dkBlendStateDefaults(&blend);
 static constexpr DkBlendFactor factors[]={DkBlendFactor_Zero,DkBlendFactor_One,DkBlendFactor_SrcColor,DkBlendFactor_InvSrcColor,DkBlendFactor_DstColor,DkBlendFactor_InvDstColor,DkBlendFactor_SrcAlpha,DkBlendFactor_InvSrcAlpha,DkBlendFactor_DstAlpha,DkBlendFactor_InvDstAlpha,DkBlendFactor_ConstColor,DkBlendFactor_InvConstColor,DkBlendFactor_ConstAlpha,DkBlendFactor_InvConstAlpha,DkBlendFactor_SrcAlphaSaturate};
 dkBlendStateSetOps(&blend,DkBlendOp(unsigned(d.Blend.EquationRgb)+1),DkBlendOp(unsigned(d.Blend.EquationAlpha)+1));
 dkBlendStateSetFactors(&blend,factors[unsigned(d.Blend.SourceRgb)],factors[unsigned(d.Blend.DestRgb)],factors[unsigned(d.Blend.SourceAlpha)],factors[unsigned(d.Blend.DestAlpha)]);dkCmdBufBindBlendState(g.cmd,0,&blend);
 dkCmdBufSetBlendConst(g.cmd,d.Blend.ConstantColor[0],d.Blend.ConstantColor[1],d.Blend.ConstantColor[2],d.Blend.ConstantColor[3]);
 DkColorWriteState write;dkColorWriteStateDefaults(&write);dkColorWriteStateSetMask(&write,0,d.ColorWriteMask);dkCmdBufBindColorWriteState(g.cmd,&write);
 DkColorState color;dkColorStateDefaults(&color);dkColorStateSetBlendEnable(&color,0,d.Blend.Enabled);
 static const DkLogicOp logic[]={DkLogicOp_Clear,DkLogicOp_And,DkLogicOp_AndReverse,DkLogicOp_Copy,DkLogicOp_Set,DkLogicOp_CopyInverted,DkLogicOp_NoOp,DkLogicOp_Invert,DkLogicOp_Nand,DkLogicOp_Or,DkLogicOp_Nor,DkLogicOp_Xor,DkLogicOp_Equivalent,DkLogicOp_AndInverted,DkLogicOp_OrReverse,DkLogicOp_OrInverted};
 if(!d.Blend.Enabled)color.logicOp=logic[unsigned(d.LogicOperation)];dkCmdBufBindColorState(g.cmd,&color);
 DkRasterizerState raster;dkRasterizerStateDefaults(&raster);raster.cullMode=d.CullMode==GfxNativeCullMode::KeepAll?DkFace_None:(d.FramebufferFlipped?DkFace_Front:DkFace_Back);raster.frontFace=d.CullMode==GfxNativeCullMode::KeepCounterClockwise?DkFrontFace_CCW:DkFrontFace_CW;dkCmdBufBindRasterizerState(g.cmd,&raster);
DkDepthStencilState depth;dkDepthStencilStateDefaults(&depth);depth.depthTestEnable=d.DepthTestEnabled||d.DepthWriteEnabled;depth.depthWriteEnable=d.DepthWriteEnabled;depth.depthCompareOp=d.DepthTestEnabled?Compare(d.DepthCompare):DkCompareOp_Always;
 depth.stencilTestEnable=d.Stencil.Enabled;depth.stencilFrontCompareOp=Compare(d.Stencil.Compare);depth.stencilBackCompareOp=depth.stencilFrontCompareOp;depth.stencilFrontFailOp=DkStencilOp(unsigned(d.Stencil.Fail)+1);depth.stencilBackFailOp=depth.stencilFrontFailOp;depth.stencilFrontPassOp=DkStencilOp(unsigned(d.Stencil.Pass)+1);depth.stencilBackPassOp=depth.stencilFrontPassOp;depth.stencilFrontDepthFailOp=DkStencilOp(unsigned(d.Stencil.DepthFail)+1);depth.stencilBackDepthFailOp=depth.stencilFrontDepthFailOp;dkCmdBufSetStencil(g.cmd,DkFace_FrontAndBack,d.Stencil.WriteMask,d.Stencil.Reference,d.Stencil.CompareMask);dkCmdBufBindDepthStencilState(g.cmd,&depth);const DkShader*pair[]={&vs.shader,&fs.shader};dkCmdBufBindShaders(g.cmd,DkStageFlag_GraphicsMask,pair,2);
 for(auto [binding,slot]:vs.uniforms){Require(binding==0,"deko vertex UBO binding unsupported");auto address=g.Upload(d.VertexUniformBytes);dkCmdBufBindUniformBuffer(g.cmd,DkStage_Vertex,slot,address,(d.VertexUniformBytes.size()+255)&~255);}
 for(auto [binding,slot]:fs.uniforms){Require(binding==4,"deko fragment UBO binding unsupported");auto address=g.Upload(d.FragmentUniformBytes);dkCmdBufBindUniformBuffer(g.cmd,DkStage_Fragment,slot,address,(d.FragmentUniformBytes.size()+255)&~255);}
 DkVtxAttribState attrs[16]{};for(auto&a:attrs)a.isFixed=true;DkVtxBufferState buffers[16]{};for(auto&b:d.VertexBindings){Require(b.Binding<16,"deko vertex binding invalid");buffers[b.Binding]={b.ByteStride,b.PerInstance?1u:0u};auto address=g.Upload(b.Bytes);DkBufExtents ext{address,b.Bytes.size()};dkCmdBufBindVtxBuffers(g.cmd,b.Binding,&ext,1);}for(auto&a:d.VertexAttributes){Require(a.Location<16&&a.ComponentCount&&a.ComponentCount<=4,"deko vertex attribute invalid");auto&out=attrs[a.Location];out.isFixed=false;out.bufferId=a.Binding;out.offset=a.ByteOffset;static const DkVtxAttribSize sizes[3][4]={{DkVtxAttribSize_1x8,DkVtxAttribSize_2x8,DkVtxAttribSize_3x8,DkVtxAttribSize_4x8},{DkVtxAttribSize_1x16,DkVtxAttribSize_2x16,DkVtxAttribSize_3x16,DkVtxAttribSize_4x16},{DkVtxAttribSize_1x32,DkVtxAttribSize_2x32,DkVtxAttribSize_3x32,DkVtxAttribSize_4x32}};unsigned type=unsigned(a.Format);out.size=sizes[type==3?2:type==2?1:0][a.ComponentCount-1];out.type=type==3?DkVtxAttribType_Float:type==1?DkVtxAttribType_Uscaled:DkVtxAttribType_Sscaled;}dkCmdBufBindVtxAttribState(g.cmd,attrs,16);dkCmdBufBindVtxBufferState(g.cmd,buffers,16);
 if(!state->fallbackColor){const std::array<uint8_t,4> white{255,255,255,255};state->fallbackColor=g.Create(1,1,DkImageFormat_RGBA8_Unorm);g.UploadImage(*state->fallbackColor,white);state->fallbackInteger=g.Create(1,1,DkImageFormat_R32_Uint);g.UploadImage(*state->fallbackInteger,white);}
 for(auto[binding,slot]:fs.textures)g.BindTexture(DkStage_Fragment,slot,fs.integerTextures.contains(binding)?*state->fallbackInteger:*state->fallbackColor,false);
 for(auto&texture:d.Textures){auto binding=fs.textures.find(unsigned(texture.Slot)+1);if(binding!=fs.textures.end()){
 Image*image=nullptr;if(texture.NativeType==2){for(auto&[key,target]:state->targets)if(std::get<0>(key)==d.RenderTargetNamespace&&std::get<1>(key)==texture.PhysicalAddress){image=target.shadow.get();break;}}
 if(!image)image=&state->Texture(texture);g.BindNativeTexture(DkStage_Fragment,binding->second,*image,texture.NativeType==2?false:texture.MinLinear,texture.NativeType==2?false:texture.MagLinear,texture.NativeWrapS,texture.NativeWrapT);
 }}
 if(!d.LightingLut.PackedEntries.empty()){
 Require(d.LightingLut.Valid(),"deko lighting LUT invalid");auto&i=state->lighting[d.LightingLut.ContentHash];if(!i){i=g.Create(256,24,DkImageFormat_R32_Uint);g.UploadImage(*i,{reinterpret_cast<const uint8_t*>(d.LightingLut.PackedEntries.data()),d.LightingLut.PackedEntries.size_bytes()});}auto b=fs.textures.find(13);if(b!=fs.textures.end())g.BindTexture(DkStage_Fragment,b->second,*i,false);
 }for(auto [binding,slot]:fs.images){Require(binding==5,"deko image binding unsupported");g.BindImage(DkStage_Fragment,slot,*t.shadow);}
 unsigned scale=d.FragmentOperationMode==3?1:3;DkViewport vp{d.ViewportX*scale,RetunedDeko::TopLeftY(float(t.color->height),d.ViewportY*scale,d.ViewportHeight*scale),d.ViewportWidth*scale,d.ViewportHeight*scale,0,1};dkCmdBufSetViewports(g.cmd,0,&vp,1);Require(d.ScissorMode==0||d.ScissorMode==1||d.ScissorMode==3,"deko scissor mode invalid");
 std::vector<DkScissor> scissors;
 const int w=int(t.color->width),h=int(t.color->height);
 auto rect=[&](int x0,int y0,int x1,int y1){x0=std::clamp(x0,0,w);y0=std::clamp(y0,0,h);x1=std::clamp(x1,0,w);y1=std::clamp(y1,0,h);if(x1>x0&&y1>y0)scissors.push_back({x0,y0,unsigned(x1-x0),unsigned(y1-y0)});};
 // PICA/ReFramed rectangles use bottom-left coordinates. Deko's render
 // target is top-left: reflect the rectangle position, not its texture UVs.
 const int x0=int(d.ScissorX1)*scale,y0=RetunedDeko::TopLeftY(h,int(d.ScissorY1)*int(scale),(int(d.ScissorY2)-int(d.ScissorY1)+1)*int(scale)),x1=(int(d.ScissorX2)+1)*scale,y1=h-int(d.ScissorY1)*scale;
 if(d.ScissorMode==0)rect(0,0,w,h);
 else if(d.ScissorMode==3)rect(x0,y0,x1,y1);
 else {for(auto r:RetunedDeko::ExcludeRect(w,h,x0,y0,x1,y1))rect(r.x,r.y,r.x+r.width,r.y+r.height);}
 DkPrimitive primitive=d.Topology==GfxNativePicaTopology::TriangleStrip?DkPrimitive_TriangleStrip:d.Topology==GfxNativePicaTopology::TriangleFan?DkPrimitive_TriangleFan:DkPrimitive_Triangles;if(d.Indexed){auto addr=g.Upload(d.IndexBytes);dkCmdBufBindIdxBuffer(g.cmd,d.IndicesAre16Bit?DkIdxFormat_Uint16:DkIdxFormat_Uint8,addr);}
 for(const auto&sc:scissors){dkCmdBufSetScissors(g.cmd,0,&sc,1);if(d.Indexed)dkCmdBufDrawIndexed(g.cmd,primitive,d.VertexCount,1,0,d.BaseVertex,0);else dkCmdBufDraw(g.cmd,primitive,d.VertexCount,1,0,0);}g.EndWork("native-draw",drawStart);return true;}catch(const std::exception&e){if(error)*error=e.what();std::printf("deko PICA draw rejected: %s\n",e.what());return false;}}
bool GfxRenderingAPIDeko::SubmitPicaDisplayTransfer(const GfxNativePicaDisplayTransferView&t,std::string*error){try{static std::map<std::tuple<unsigned,unsigned,unsigned>,bool> seenTransfers;auto transferKey=std::make_tuple(t.Flags,unsigned(t.InputWidth),unsigned(t.InputHeight));if(seenTransfers.emplace(transferKey,true).second){std::printf("deko transfer flags=%08x input=%ux%u output=%ux%u present=%d mode=%u\n",t.Flags,t.InputWidth,t.InputHeight,t.OutputWidth,t.OutputHeight,t.Present,unsigned(t.PresentationMode));std::fflush(stdout);}auto i=std::find_if(state->targets.begin(),state->targets.end(),[&](auto&x){return std::get<0>(x.first)==t.RenderTargetNamespace&&std::get<1>(x.first)==t.InputPhysicalAddress;});Require(i!=state->targets.end(),"deko transfer source missing");Require(t.TextureCopyBytes==0,"deko raw texture copy not implemented");if(t.Present){auto&g=*state->gpu;dkCmdBufBarrier(g.cmd,DkBarrier_Full,DkInvalidateFlags_Image);g.Bind(g.Screen());Raster(g,t.PresentationMode==GfxNativePicaPresentationMode::AlphaOverlay);auto&vs=g.shaders->Get(DkStage_Vertex,ScanVertex);auto&fs=g.shaders->Get(DkStage_Fragment,ScanFragment);const DkShader*pair[]={&vs.shader,&fs.shader};dkCmdBufBindShaders(g.cmd,DkStageFlag_GraphicsMask,pair,2);g.BindTexture(DkStage_Fragment,0,*i->second.color);dkCmdBufDraw(g.cmd,DkPrimitive_Triangles,3,1,0,0);g.Submit(true,"transfer");}return true;}catch(const std::exception&e){if(error)*error=e.what();return false;}}
bool GfxRenderingAPIDeko::QueuePicaCompletion(uint64_t id,std::string*){state->gpu->Submit(false,"completion");state->completions.push_back(id);return true;}
std::vector<uint64_t> GfxRenderingAPIDeko::TakePicaCompletions(){auto out=std::move(state->completions);state->completions.clear();return out;}
bool GfxRenderingAPIDeko::ClearPicaRenderTarget(uint64_t ns,uint32_t address,std::string*){for(auto&[k,t]:state->targets)if(std::get<0>(k)==ns&&std::get<1>(k)==address){state->gpu->Bind(*t.color,t.depth.get());dkCmdBufClearColorFloat(state->gpu->cmd,0,DkColorMask_RGBA,0,0,0,0);}return true;}
bool GfxRenderingAPIDeko::SubmitPicaMemoryFill(const GfxNativePicaMemoryFillView&fill,std::string*){Require(fill.StartPhysicalAddress&&fill.EndPhysicalAddress>fill.StartPhysicalAddress&&(fill.Control&1),"deko memory fill invalid");auto i=std::find_if(state->fills.begin(),state->fills.end(),[&](auto&v){return v.RenderTargetNamespace==fill.RenderTargetNamespace&&v.StartPhysicalAddress==fill.StartPhysicalAddress&&v.EndPhysicalAddress==fill.EndPhysicalAddress;});if(i!=state->fills.end())*i=fill;else state->fills.push_back(fill);for(auto&[k,t]:state->targets)state->ApplyFills(k,t);return true;}
bool GfxRenderingAPIDeko::ResetPicaState(std::string*){state->gpu->Submit();state->targets.clear();state->nativeTextures.clear();state->textureBytes=0;state->fills.clear();state->completions.clear();return true;}
void RetunedDekoGuiInit(){Require(active,"deko GUI has no renderer");active->GuiInit();}
void RetunedDekoGuiRender(ImDrawData*data){Require(active,"deko GUI has no renderer");active->GuiRender(data);}
void RetunedDekoPresent(){Require(active,"deko presentation has no renderer");active->Present();}
void GfxRenderingAPIDeko::UnloadShader(ShaderProgram* oldPrg){throw std::runtime_error("deko backend operation not implemented: UnloadShader");}

void GfxRenderingAPIDeko::LoadShader(ShaderProgram* newPrg){throw std::runtime_error("deko backend operation not implemented: LoadShader");}

ShaderProgram* GfxRenderingAPIDeko::CreateAndLoadNewShader(uint64_t shaderId0, uint64_t shaderId1){throw std::runtime_error("deko backend operation not implemented: CreateAndLoadNewShader");}

ShaderProgram* GfxRenderingAPIDeko::LookupShader(uint64_t shaderId0, uint64_t shaderId1){throw std::runtime_error("deko backend operation not implemented: LookupShader");}

void GfxRenderingAPIDeko::ShaderGetInfo(ShaderProgram* prg, uint8_t* numInputs, bool usedTextures[2]){throw std::runtime_error("deko backend operation not implemented: ShaderGetInfo");}

void GfxRenderingAPIDeko::ClearShaderCache(){throw std::runtime_error("deko backend operation not implemented: ClearShaderCache");}

bool GfxRenderingAPIDeko::UploadTextureMipLevel(uint32_t level, const uint8_t* rgba32Buf, uint32_t width, uint32_t height){throw std::runtime_error("deko backend operation not implemented: UploadTextureMipLevel");}

bool GfxRenderingAPIDeko::SetNativeSamplerParameters(int sampler, const GfxNativeSamplerState& state){throw std::runtime_error("deko backend operation not implemented: SetNativeSamplerParameters");}

void GfxRenderingAPIDeko::SetDepthTestAndMask(bool depth_test, bool z_upd){throw std::runtime_error("deko backend operation not implemented: SetDepthTestAndMask");}

void GfxRenderingAPIDeko::SetCurrentPrimDepth(float depth){throw std::runtime_error("deko backend operation not implemented: SetCurrentPrimDepth");}

void GfxRenderingAPIDeko::SetZmodeDecal(bool decal){throw std::runtime_error("deko backend operation not implemented: SetZmodeDecal");}

void GfxRenderingAPIDeko::SetViewport(int x, int y, int width, int height){DkViewport v{float(x),float(y),float(width),float(height),0,1};dkCmdBufSetViewports(state->gpu->cmd,0,&v,1);}

void GfxRenderingAPIDeko::SetScissor(int x, int y, int width, int height){Require(width>=0&&height>=0,"deko scissor extent invalid");DkScissor sc{x,y,unsigned(width),unsigned(height)};dkCmdBufSetScissors(state->gpu->cmd,0,&sc,1);}

void GfxRenderingAPIDeko::SetUseAlpha(bool useAlpha){throw std::runtime_error("deko backend operation not implemented: SetUseAlpha");}

bool GfxRenderingAPIDeko::SetNativeBlendState(const GfxNativeBlendState& state){throw std::runtime_error("deko backend operation not implemented: SetNativeBlendState");}

bool GfxRenderingAPIDeko::SetNativeCullMode(GfxNativeCullMode mode){throw std::runtime_error("deko backend operation not implemented: SetNativeCullMode");}

bool GfxRenderingAPIDeko::SetOot3dNativeTransform(const float* row_major_matrix){throw std::runtime_error("deko backend operation not implemented: SetOot3dNativeTransform");}

bool GfxRenderingAPIDeko::DrawTrianglesCached(uint64_t cache_id, uint64_t content_version, const float* buf_vbo, size_t buf_vbo_len, size_t buf_vbo_num_tris){throw std::runtime_error("deko backend operation not implemented: DrawTrianglesCached");}

void GfxRenderingAPIDeko::DrawTriangles(float buf_vbo[], size_t buf_vbo_len, size_t buf_vbo_num_tris){throw std::runtime_error("deko backend operation not implemented: DrawTriangles");}

bool GfxRenderingAPIDeko::UpdateFramebufferParametersWithColorFormat(int fb_id, uint32_t width, uint32_t height, uint32_t msaa_level, bool opengl_invertY, bool render_target, bool has_depth_buffer, bool can_extract_depth, GfxFramebufferColorFormat color_format){Require(color_format==GfxFramebufferColorFormat::Rgba8,"deko legacy integer framebuffer not implemented");UpdateFramebufferParameters(fb_id,width,height,msaa_level,opengl_invertY,render_target,has_depth_buffer,can_extract_depth);return true;}

bool GfxRenderingAPIDeko::SupportsOot3dShadow2dR32uiPipeline()const{return false;}

bool GfxRenderingAPIDeko::BindOot3dShadow2dTexture(int fb_id, uint32_t texture_unit){throw std::runtime_error("deko backend operation not implemented: BindOot3dShadow2dTexture");}

bool GfxRenderingAPIDeko::SetOot3dShadow2dShaderParameters(uint32_t texture_bias, bool orthographic, bool invert){throw std::runtime_error("deko backend operation not implemented: SetOot3dShadow2dShaderParameters");}

bool GfxRenderingAPIDeko::SupportsOot3dPicaFogLut()const{return false;}

bool GfxRenderingAPIDeko::SetOot3dPicaFogShaderParameters(const uint32_t* lut_words, size_t lut_word_count, bool flip, uint64_t state_key){throw std::runtime_error("deko backend operation not implemented: SetOot3dPicaFogShaderParameters");}

bool GfxRenderingAPIDeko::SetOot3dPicaAlphaTestShaderParameters(bool enabled, uint32_t compare_func, uint8_t reference){throw std::runtime_error("deko backend operation not implemented: SetOot3dPicaAlphaTestShaderParameters");}

bool GfxRenderingAPIDeko::SupportsOot3dPicaTexture2()const{return false;}

GfxNativePicaBackendStats GfxRenderingAPIDeko::GetNativePicaBackendStats()const noexcept{return {};}

void GfxRenderingAPIDeko::SetNativePicaGeometryCacheEnabled(bool enabled)noexcept{}

bool GfxRenderingAPIDeko::StartOot3dShadow2dDepthEncodePass(int fb_id, uint32_t clear_value){throw std::runtime_error("deko backend operation not implemented: StartOot3dShadow2dDepthEncodePass");}

void GfxRenderingAPIDeko::EndOot3dShadow2dDepthEncodePass(){throw std::runtime_error("deko backend operation not implemented: EndOot3dShadow2dDepthEncodePass");}

bool GfxRenderingAPIDeko::DrawOot3dShadow2dDepthEncodedTriangles(float buf_vbo[], size_t buf_vbo_len, size_t buf_vbo_num_tris){throw std::runtime_error("deko backend operation not implemented: DrawOot3dShadow2dDepthEncodedTriangles");}

void GfxRenderingAPIDeko::CopyFramebuffer(int fbDstId, int fbSrcId, int srcX0, int srcY0, int srcX1, int srcY1, int dstX0, int dstY0, int dstX1, int dstY1){throw std::runtime_error("deko backend operation not implemented: CopyFramebuffer");}

void GfxRenderingAPIDeko::ClearDepthRegion(int x, int y, int w, int h){throw std::runtime_error("deko backend operation not implemented: ClearDepthRegion");}

void GfxRenderingAPIDeko::ReadFramebufferToCPU(int fbId, uint32_t width, uint32_t height, uint16_t* rgba16Buf){throw std::runtime_error("deko backend operation not implemented: ReadFramebufferToCPU");}

void GfxRenderingAPIDeko::ResolveMSAAColorBuffer(int fbIdTarger, int fbIdSrc){throw std::runtime_error("deko backend operation not implemented: ResolveMSAAColorBuffer");}

std::unordered_map<std::pair<float, float>, uint16_t, hash_pair_ff> GfxRenderingAPIDeko::GetPixelDepth(int fb_id, const std::set<std::pair<float, float>>& coordinates){throw std::runtime_error("deko backend operation not implemented: GetPixelDepth");}

void GfxRenderingAPIDeko::SelectTextureFb(int fbId){state->selectedTexture=0x40000000u|unsigned(fbId);}

}
