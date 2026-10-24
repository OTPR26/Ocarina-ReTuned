// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <deko3d.h>
#include <memory>
#include <span>
#include <vector>
#include <map>
#include <tuple>
#include <string>
#include <cstdint>
#include "shaders.h"
namespace RetunedDeko {
struct Image {
 DkMemBlock memory{};DkImage image{};DkImageView view{};unsigned width{},height{},descriptor=~0u,storageDescriptor=~0u;
 uint64_t allocatedBytes=0;
 std::shared_ptr<std::vector<unsigned>> freeDescriptors;
 ~Image(){if(memory)dkMemBlockDestroy(memory);if(freeDescriptors){if(descriptor!=~0u)freeDescriptors->push_back(descriptor);if(storageDescriptor!=~0u)freeDescriptors->push_back(storageDescriptor);}}
};
class Gpu {
 unsigned uploadCursor=0,descriptorCursor=0;
 std::shared_ptr<std::vector<unsigned>> freeDescriptors=std::make_shared<std::vector<unsigned>>();
 unsigned AllocateDescriptor();
 unsigned samplerCursor=2;
 std::map<std::tuple<bool,bool,unsigned,unsigned>,unsigned> nativeSamplers;
 DkMemBlock commands{},uploads{},descriptors{};
 bool profiling=false;
 uint64_t profileFrame=0,profileStart=0,profileWait=0,profileAcquire=0,profileBytes=0,profileImages=0;
 std::map<std::string,std::pair<unsigned,uint64_t>> profileSubmits;
 DkSwapchain swapchain{};std::unique_ptr<Image> screen[2];int slot=-1;
public:
 DkDevice device{};DkQueue queue{};DkCmdBuf cmd{};
 std::unique_ptr<Shaders> shaders;
 Gpu();~Gpu();
 uint64_t BeginWork() const;
 void EndWork(const char*,uint64_t);
 void BeginProfileFrame();
 void Submit(bool recycle=false,const char* reason="other");
 DkGpuAddr Upload(std::span<const unsigned char>,unsigned align=256);
 std::unique_ptr<Image> Create(unsigned w,unsigned h,DkImageFormat format,bool present=false,bool storage=false);
 void UploadImage(Image&,std::span<const unsigned char>,unsigned maxStripRows=~0u);
 void Bind(Image&,Image*depth=nullptr);
 void BindImage(DkStage,unsigned,Image&);
 void BindTexture(DkStage,unsigned,Image&,bool linear=true);
 void BindNativeTexture(DkStage,unsigned,Image&,bool minLinear,bool magLinear,unsigned wrapS,unsigned wrapT);
 Image& Screen();void Present();
 std::vector<unsigned char> Read(Image&);
};
}
