// SPDX-License-Identifier: GPL-2.0-or-later
#include "gpu.h"
#include <switch.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <chrono>
#include <filesystem>
namespace RetunedDeko {
namespace {
constexpr unsigned CommandSize=4*1024*1024, UploadSize=32*1024*1024,DescriptorSize=256*1024;
uint64_t Micros(){return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
unsigned Align(unsigned n,unsigned a){return(n+a-1)&~(a-1);}
void Check(bool b,const char*m){if(!b)throw std::runtime_error(m);}
DkMemBlock Memory(DkDevice d,unsigned n,unsigned flags){DkMemBlockMaker m;dkMemBlockMakerDefaults(&m,d,Align(n,DK_MEMBLOCK_ALIGNMENT));m.flags=flags;auto p=dkMemBlockCreate(&m);Check(p,"deko GPU memory allocation failed");return p;}
void Debug(void*,const char*where,DkResult result,const char*message){std::printf("deko GPU diagnostic %d %s: %s\n",int(result),where?where:"",message?message:"");}
}
unsigned Gpu::AllocateDescriptor(){if(!freeDescriptors->empty()){auto n=freeDescriptors->back();freeDescriptors->pop_back();return n;}Check(descriptorCursor<4096,"deko texture descriptor arena full");return descriptorCursor++;}
Gpu::Gpu(){profiling=std::filesystem::exists("sdmc:/switch/oot3dre/profile-renderer.flag");std::puts("deko stage=device");
 DkDeviceMaker d;dkDeviceMakerDefaults(&d);d.flags=DkDeviceFlags_OriginUpperLeft|DkDeviceFlags_DepthZeroToOne;d.cbDebug=Debug;device=dkDeviceCreate(&d);Check(device,"deko device unavailable");
 std::puts("deko stage=queue");DkQueueMaker q;dkQueueMakerDefaults(&q,device);q.flags=DkQueueFlags_Graphics;q.perWarpScratchMemorySize=65536;queue=dkQueueCreate(&q);Check(queue,"deko queue unavailable");
 std::puts("deko stage=command-memory");commands=Memory(device,CommandSize,DkMemBlockFlags_CpuUncached|DkMemBlockFlags_GpuCached);std::puts("deko stage=upload-memory");uploads=Memory(device,UploadSize,DkMemBlockFlags_CpuUncached|DkMemBlockFlags_GpuCached);std::puts("deko stage=descriptors");descriptors=Memory(device,DescriptorSize,DkMemBlockFlags_CpuUncached|DkMemBlockFlags_GpuCached|DkMemBlockFlags_ZeroFillInit);
 for(unsigned n=0;n<2;n++){DkSampler sampler;dkSamplerDefaults(&sampler);sampler.minFilter=n?DkFilter_Linear:DkFilter_Nearest;sampler.magFilter=sampler.minFilter;auto*p=static_cast<unsigned char*>(dkMemBlockGetCpuAddr(descriptors))+128*1024+n*32;dkSamplerDescriptorInitialize(reinterpret_cast<DkSamplerDescriptor*>(p),&sampler);}
 DkCmdBufMaker c;dkCmdBufMakerDefaults(&c,device);cmd=dkCmdBufCreate(&c);dkCmdBufAddMemory(cmd,commands,0,CommandSize);
 std::puts("deko stage=screen-images");for(auto&i:screen)i=Create(1280,720,DkImageFormat_RGBA8_Unorm,true);const DkImage*images[]={&screen[0]->image,&screen[1]->image};std::puts("deko stage=swapchain");DkSwapchainMaker sm;dkSwapchainMakerDefaults(&sm,device,nwindowGetDefault(),images,2);swapchain=dkSwapchainCreate(&sm);Check(swapchain,"deko swapchain unavailable");std::puts("deko stage=shader-arena");shaders=std::make_unique<Shaders>(device);if(std::filesystem::exists("sdmc:/switch/oot3dre/check-texture-upload.flag")) {
  auto image=Create(64,64,DkImageFormat_RGBA8_Unorm);
  std::vector<unsigned char> expected(64*64*4);
  for(unsigned y=0;y<64;++y)for(unsigned x=0;x<64;++x){auto n=(y*64+x)*4;expected[n]=x*3;expected[n+1]=y*3;expected[n+2]=(x^y)*3;expected[n+3]=255;}
  UploadImage(*image,expected,8);
  Check(Read(*image)==expected,"deko striped texture upload/readback mismatch");
  std::puts("deko striped texture upload/readback PASS pixels=4096 strips=8");
 }
 std::puts("Ocarina ReTuned deko3d renderer initialized");
}
Gpu::~Gpu(){if(queue)dkQueueWaitIdle(queue);shaders.reset();if(swapchain)dkSwapchainDestroy(swapchain);for(auto&i:screen)i.reset();if(cmd)dkCmdBufDestroy(cmd);for(auto m:{commands,uploads,descriptors})if(m)dkMemBlockDestroy(m);if(queue)dkQueueDestroy(queue);if(device)dkDeviceDestroy(device);}
uint64_t Gpu::BeginWork()const{return profiling?Micros():0;}
void Gpu::EndWork(const char*name,uint64_t start){if(start){auto&sample=profileSubmits[name];++sample.first;sample.second+=Micros()-start;}}
void Gpu::BeginProfileFrame(){if(!profiling)return;profileStart=Micros();profileWait=profileAcquire=profileBytes=profileImages=0;profileSubmits.clear();}
void Gpu::Submit(bool recycle,const char* reason){auto start=profiling?Micros():0;dkQueueSubmitCommands(queue,dkCmdBufFinishList(cmd));DkFence f;dkQueueSignalFence(queue,&f,true);dkQueueFlush(queue);auto wait=profiling?Micros():0;Check(dkFenceWait(&f,30'000'000'000LL)==DkResult_Success,"deko GPU fence timeout");if(profiling){profileWait+=Micros()-wait;auto&sample=profileSubmits[reason];++sample.first;sample.second+=Micros()-start;}Check(!dkQueueIsInErrorState(queue),"deko GPU queue error");dkCmdBufClear(cmd);dkCmdBufAddMemory(cmd,commands,0,CommandSize);if(recycle)uploadCursor=0;}

DkGpuAddr Gpu::Upload(std::span<const unsigned char>b,unsigned align){Check(b.size()<=UploadSize,"deko upload exceeds staging arena");unsigned start=Align(uploadCursor,align);if(start+b.size()>UploadSize){Submit(true,"upload-full");start=0;}if(profiling)profileBytes+=b.size();memcpy(static_cast<unsigned char*>(dkMemBlockGetCpuAddr(uploads))+start,b.data(),b.size());uploadCursor=start+Align(b.size(),256);return dkMemBlockGetGpuAddr(uploads)+start;}
std::unique_ptr<Image> Gpu::Create(unsigned w,unsigned h,DkImageFormat format,bool present,bool storage){Check(w&&h&&w<=8192&&h<=8192,"deko image extent invalid");auto i=std::make_unique<Image>();i->width=w;i->height=h;DkImageLayoutMaker m;dkImageLayoutMakerDefaults(&m,device);m.flags=DkImageFlags_UsageRender|DkImageFlags_Usage2DEngine|(present?DkImageFlags_UsagePresent:0)|(storage?DkImageFlags_UsageLoadStore:0);m.format=format;m.dimensions[0]=w;m.dimensions[1]=h;DkImageLayout layout;dkImageLayoutInitialize(&layout,&m);i->allocatedBytes=Align(dkImageLayoutGetSize(&layout),DK_MEMBLOCK_ALIGNMENT);i->memory=Memory(device,dkImageLayoutGetSize(&layout),DkMemBlockFlags_Image|DkMemBlockFlags_GpuCached);dkImageInitialize(&i->image,&layout,i->memory,0);dkImageViewDefaults(&i->view,&i->image);i->freeDescriptors=freeDescriptors;i->descriptor=AllocateDescriptor();auto*p=static_cast<unsigned char*>(dkMemBlockGetCpuAddr(descriptors))+i->descriptor*32;dkImageDescriptorInitialize(reinterpret_cast<DkImageDescriptor*>(p),&i->view,false,false);return i;}
void Gpu::UploadImage(Image&i,std::span<const unsigned char>bytes,unsigned maxStripRows){
 if(profiling)++profileImages;
 Check(bytes.size()==size_t(i.width)*i.height*4,"deko image upload extent mismatch");
 // A mobile pack can contain 4096-square atlases, larger than the staging
 // arena. Upload complete row strips; Upload fences before recycling memory.
 const size_t rowBytes=size_t(i.width)*4;
 const unsigned maxRows=std::min(unsigned(UploadSize/rowBytes),maxStripRows);
 Check(maxRows>0,"deko texture row exceeds staging arena");
 for(unsigned y=0;y<i.height;){
  unsigned rows=std::min(maxRows,i.height-y);
  // deko3d rowLength and imageHeight are byte strides, not pixels/rows.
  DkCopyBuf from{Upload(bytes.subspan(size_t(y)*rowBytes,size_t(rows)*rowBytes)),unsigned(rowBytes),unsigned(size_t(rows)*rowBytes)};
  DkImageRect rect{0,y,0,i.width,rows,1};dkCmdBufCopyBufferToImage(cmd,&from,&i.view,&rect,0);
  y+=rows;
 }
 dkCmdBufBarrier(cmd,DkBarrier_Full,DkInvalidateFlags_Image|DkInvalidateFlags_Descriptors);
}

void Gpu::Bind(Image&color,Image*depth){dkCmdBufBindRenderTarget(cmd,&color.view,depth?&depth->view:nullptr);DkViewport vp{0,0,float(color.width),float(color.height),0,1};DkScissor sc{0,0,color.width,color.height};dkCmdBufSetViewports(cmd,0,&vp,1);dkCmdBufSetScissors(cmd,0,&sc,1);}
void Gpu::BindTexture(DkStage stage,unsigned slot,Image&i,bool linear){auto base=dkMemBlockGetGpuAddr(descriptors);dkCmdBufBindImageDescriptorSet(cmd,base,4096);dkCmdBufBindSamplerDescriptorSet(cmd,base+128*1024,4096);DkResHandle handle=dkMakeTextureHandle(i.descriptor,linear?1:0);dkCmdBufBindTextures(cmd,stage,slot,&handle,1);}

void Gpu::BindNativeTexture(DkStage stage,unsigned slot,Image&i,bool minLinear,bool magLinear,unsigned wrapS,unsigned wrapT){
 auto wrap=[](unsigned value){switch(value){case 0:return DkWrapMode_ClampToEdge;case 2:case 6:case 7:return DkWrapMode_Repeat;case 3:return DkWrapMode_MirroredRepeat;default:throw std::runtime_error("deko native asymmetric/border wrap requires additional state");}};
 const auto key=std::make_tuple(minLinear,magLinear,wrapS,wrapT);auto found=nativeSamplers.find(key);
 if(found==nativeSamplers.end()){Check(samplerCursor<4096,"deko sampler descriptor arena full");DkSampler sampler;dkSamplerDefaults(&sampler);sampler.minFilter=minLinear?DkFilter_Linear:DkFilter_Nearest;sampler.magFilter=magLinear?DkFilter_Linear:DkFilter_Nearest;sampler.wrapMode[0]=wrap(wrapS);sampler.wrapMode[1]=wrap(wrapT);auto*p=static_cast<unsigned char*>(dkMemBlockGetCpuAddr(descriptors))+128*1024+samplerCursor*32;dkSamplerDescriptorInitialize(reinterpret_cast<DkSamplerDescriptor*>(p),&sampler);found=nativeSamplers.emplace(key,samplerCursor++).first;}
 auto base=dkMemBlockGetGpuAddr(descriptors);dkCmdBufBindImageDescriptorSet(cmd,base,4096);dkCmdBufBindSamplerDescriptorSet(cmd,base+128*1024,4096);DkResHandle handle=dkMakeTextureHandle(i.descriptor,found->second);dkCmdBufBindTextures(cmd,stage,slot,&handle,1);
}

void Gpu::BindImage(DkStage stage,unsigned slot,Image&i){if(i.storageDescriptor==~0u){i.storageDescriptor=AllocateDescriptor();auto*p=static_cast<unsigned char*>(dkMemBlockGetCpuAddr(descriptors))+i.storageDescriptor*32;dkImageDescriptorInitialize(reinterpret_cast<DkImageDescriptor*>(p),&i.view,true,false);}dkCmdBufBindImageDescriptorSet(cmd,dkMemBlockGetGpuAddr(descriptors),4096);DkResHandle handle=i.storageDescriptor;dkCmdBufBindImages(cmd,stage,slot,&handle,1);}
Image& Gpu::Screen(){if(slot<0){auto acquireStart=profiling?Micros():0;slot=dkQueueAcquireImage(queue,swapchain);if(profiling)profileAcquire+=Micros()-acquireStart;Check(slot>=0&&slot<2,"deko swapchain acquisition failed");}return *screen[slot];}
void Gpu::Present(){if(slot<0)return;Submit(true,"present");auto start=profiling?Micros():0;dkQueuePresentImage(queue,swapchain,slot);dkQueueFlush(queue);slot=-1;if(profiling){auto end=Micros();auto elapsed=profileStart?end-profileStart:0;++profileFrame;if(profileFrame<=4||profileFrame%30==0||elapsed>100000){std::printf("deko profile frame=%llu total_us=%llu fence_us=%llu acquire_us=%llu present_us=%llu upload_bytes=%llu images=%llu",(unsigned long long)profileFrame,(unsigned long long)elapsed,(unsigned long long)profileWait,(unsigned long long)profileAcquire,(unsigned long long)(end-start),(unsigned long long)profileBytes,(unsigned long long)profileImages);for(auto&[name,sample]:profileSubmits)std::printf(" %s=%u/%llu",name.c_str(),sample.first,(unsigned long long)sample.second);std::puts("");std::fflush(stdout);}}}
std::vector<unsigned char> Gpu::Read(Image&i){std::vector<unsigned char>bytes(size_t(i.width)*i.height*4);std::vector<unsigned char>empty(bytes.size());auto address=Upload(empty);DkCopyBuf dst{address,0,0};DkImageRect rect{0,0,0,i.width,i.height,1};dkCmdBufBarrier(cmd,DkBarrier_Full,DkInvalidateFlags_L2Cache);dkCmdBufCopyImageToBuffer(cmd,&i.view,&rect,&dst,0);Submit(false,"readback");auto offset=address-dkMemBlockGetGpuAddr(uploads);memcpy(bytes.data(),static_cast<unsigned char*>(dkMemBlockGetCpuAddr(uploads))+offset,bytes.size());return bytes;}
}
