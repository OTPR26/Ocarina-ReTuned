// SPDX-License-Identifier: GPL-2.0-or-later
#include "shaders.h"
#include "shader_compat.h"
#include "uam_api.h"
#include <switch.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <pthread.h>
#include <regex>
#include <stdexcept>
#include <array>
#include <mutex>
#include <condition_variable>
#include <exception>
namespace RetunedDeko {
namespace {
constexpr unsigned Arena=64*1024*1024;
constexpr const char* Abi="retuned-deko-v1-uam-44dc0e23-patches1-10-static-local-tev";
std::string Hash(const std::string& value){
 std::array<unsigned char,32> bytes{};sha256CalculateHash(bytes.data(),value.data(),value.size());
 std::string out;for(auto n:bytes){out+="0123456789abcdef"[n>>4];out+="0123456789abcdef"[n&15];}return out;
}
bool Valid(const std::vector<unsigned char>& b,DkStage stage){
 if(b.size()<512||b.size()>8*1024*1024)return false;unsigned h[6];memcpy(h,b.data(),24);
 if(h[0]!=0x48534b44||h[1]!=24||h[5]!=1||h[2]%256||h[3]%256||size_t(h[2])+h[3]!=b.size()||h[4]<24||h[4]+64>h[2])return false;
 unsigned p[6];memcpy(p,b.data()+h[4],24);return p[0]==(stage==DkStage_Vertex?0u:1u)&&p[1]<h[3]&&p[3]<=h[3]&&p[4]<=h[3]-p[3]&&p[5]<=65536;
}
}
struct CompilerWorker {
 std::mutex mutex;std::condition_variable changed;pthread_t thread{};
 bool stopping=false,pending=false,finished=false;DkStage stage{};
 std::string source;uam::Result result;std::exception_ptr failure;
 static void* Run(void* p){auto&w=*static_cast<CompilerWorker*>(p);
  uam::init(true);
  std::unique_lock lock(w.mutex);
  for(;;){w.changed.wait(lock,[&]{return w.pending||w.stopping;});if(w.stopping)break;
   lock.unlock();try{w.result=uam::compile(w.stage==DkStage_Vertex?uam::Stage::Vertex:uam::Stage::Fragment,w.source.c_str());}catch(...){w.failure=std::current_exception();}lock.lock();
   w.pending=false;w.finished=true;w.changed.notify_all();
  }
  lock.unlock();uam::shutdown();return nullptr;
 }
 CompilerWorker(){pthread_attr_t attr;pthread_attr_init(&attr);pthread_attr_setstacksize(&attr,8*1024*1024);int rc=pthread_create(&thread,&attr,Run,this);pthread_attr_destroy(&attr);if(rc)throw std::runtime_error("deko compiler worker unavailable");}
 ~CompilerWorker(){{std::lock_guard lock(mutex);stopping=true;changed.notify_all();}pthread_join(thread,nullptr);}
 uam::Result Get(DkStage s,std::string text){std::unique_lock lock(mutex);stage=s;source=std::move(text);finished=false;failure=nullptr;pending=true;changed.notify_all();changed.wait(lock,[&]{return finished;});if(failure)std::rethrow_exception(failure);return std::move(result);}
};
Shaders::Shaders(DkDevice d):device(d){DkMemBlockMaker m;dkMemBlockMakerDefaults(&m,d,Arena);m.flags=DkMemBlockFlags_Code|DkMemBlockFlags_CpuUncached|DkMemBlockFlags_GpuCached;code=dkMemBlockCreate(&m);if(!code)throw std::runtime_error("deko shader arena allocation failed");}
Shaders::~Shaders(){if(code)dkMemBlockDestroy(code);}
Module& Shaders::Get(DkStage stage,std::string source){
 // Exact canonical-source lookup avoids recomputing SHA-256 on every draw.
 // Persistent disk entries remain SHA-256 checked below on cache misses.
 auto key=std::make_pair(int(stage),source);if(auto i=modules.find(key);i!=modules.end())return i->second;
 if(source.size()>1024*1024||source.find("#version 450")!=0)throw std::runtime_error("deko expects canonical GLSL450");
 RetunedSwitchShader::Rewrite(source);
 if(stage==DkStage_Fragment){for(const auto*member:{"program.stages","inputs.constants"}){
  std::string expression=std::string(member)+"[stage]",selection="(";for(int n=0;n<5;n++)selection+="stage == "+std::to_string(n)+" ? "+member+"["+std::to_string(n)+"] : ";selection+=std::string(member)+"[5])";
  size_t p=0;while((p=source.find(expression,p))!=std::string::npos){source.replace(p,expression.size(),selection);p+=selection.size();}
 }}
 Module result;std::regex decl(R"(layout\(set\s*=\s*0\s*,\s*binding\s*=\s*([0-9]+)([^)]*)\)\s*uniform\s+(\w+)\s*(\{|\w+))");
 struct Binding{size_t p,n;unsigned binding;bool ubo;std::string type,tail;};std::vector<Binding> bindings;
 for(std::sregex_iterator i(source.begin(),source.end(),decl),end;i!=end;++i){const auto&m=*i;bindings.push_back({size_t(m.position()),size_t(m.length()),unsigned(std::stoul(m[1])),m[4]=="{",m[3],m[4]});}
 for(unsigned kind=0;kind<3;++kind){std::vector<unsigned> ids;for(auto&b:bindings){unsigned type=b.ubo?0:b.type.find("image")!=std::string::npos?2:1;if(type==kind)ids.push_back(b.binding);}std::sort(ids.begin(),ids.end());if(std::adjacent_find(ids.begin(),ids.end())!=ids.end())throw std::runtime_error("deko duplicate resource binding");for(unsigned i=0;i<ids.size();i++)(kind==0?result.uniforms:kind==1?result.textures:result.images)[ids[i]]=i;}
 for(auto& b:bindings)if(!b.ubo&&b.type.find("image")==std::string::npos&&(b.type.starts_with("usampler")||b.type.starts_with("isampler")))result.integerTextures.insert(b.binding);
 for(auto i=bindings.rbegin();i!=bindings.rend();++i){bool image=i->type.find("image")!=std::string::npos;unsigned slot=(i->ubo?result.uniforms:image?result.images:result.textures).at(i->binding);source.replace(i->p,i->n,"layout(binding="+std::to_string(slot)+(i->ubo?", std140":image?", r32ui":"")+") uniform "+i->type+" "+i->tail);}
 if(source.find("set=")!=std::string::npos||source.find("uniform int retuned_exclude")!=std::string::npos)throw std::runtime_error("deko unconverted shader interface");
 const auto identity=Hash(std::string(Abi)+std::to_string(int(stage))+source);const auto folder=std::filesystem::path("sdmc:/switch/oot3dre/cache/deko3d")/Abi;std::error_code ec;std::filesystem::create_directories(folder,ec);const auto path=folder/(identity+".rtcache");std::vector<unsigned char> binary;
 {std::ifstream f(path,std::ios::binary|std::ios::ate);auto n=f?f.tellg():std::streampos(-1);if(n>=576&&n<=8*1024*1024+64){binary.resize(size_t(n));f.seekg(0);f.read(reinterpret_cast<char*>(binary.data()),binary.size());if(f){std::string expected(binary.end()-64,binary.end());binary.resize(binary.size()-64);if(Hash(std::string(reinterpret_cast<const char*>(binary.data()),binary.size()))!=expected||!Valid(binary,stage))binary.clear();}else binary.clear();}}
 if(binary.empty()){
  if(!compiler)compiler=std::make_unique<CompilerWorker>();
  auto result=compiler->Get(stage,std::move(source));
  if(!result.ok||!Valid(result.dksh,stage))throw std::runtime_error("deko shader compilation failed: "+result.log);binary=std::move(result.dksh);
  auto temp=path;temp+=".new";{std::ofstream f(temp,std::ios::binary);f.write(reinterpret_cast<const char*>(binary.data()),binary.size());auto checksum=Hash(std::string(reinterpret_cast<const char*>(binary.data()),binary.size()));f.write(checksum.data(),checksum.size());f.flush();if(!f)throw std::runtime_error("deko cache write failed");}std::filesystem::rename(temp,path,ec);
  if(ec){std::filesystem::remove(path,ec);ec.clear();std::filesystem::rename(temp,path,ec);}
  if(ec)throw std::runtime_error("deko cache activation failed");
  std::printf("deko shader compiled %s bytes=%zu\n",identity.c_str(),binary.size());
 }else std::printf("deko shader cache hit %s\n",identity.c_str());
 std::fflush(stdout);
 unsigned extent=(binary.size()+255u)&~255u;if(cursor+extent>Arena-DK_SHADER_CODE_UNUSABLE_SIZE)throw std::runtime_error("deko shader arena full");memcpy(static_cast<unsigned char*>(dkMemBlockGetCpuAddr(code))+cursor,binary.data(),binary.size());DkShaderMaker m;dkShaderMakerDefaults(&m,code,cursor);dkShaderInitialize(&result.shader,&m);cursor+=extent;if(!dkShaderIsValid(&result.shader))throw std::runtime_error("deko shader module invalid");return modules.emplace(key,std::move(result)).first->second;
}
}
