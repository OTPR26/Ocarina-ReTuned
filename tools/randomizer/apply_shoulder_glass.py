"""Apply shared shoulder and action artwork to normal and retained game images."""
from pathlib import Path
from apply_android_session import patch
from apply_host_services import BASE

def install(engine):
    header=engine/BASE/'retuned_touch_hud_runtime.h'
    candidate=engine/BASE/'oot3d_native_a32_candidate_dispatch.cpp'
    if 'touchHud.ShadeBumperPositions(*dispatch.Memory);' in candidate.read_text():
        return
    patch(header,'#include "legacy_hud_anchor.h"','#include "legacy_hud_anchor.h"\n#include "../reframed/manual_jump_hud.h"')
    patch(header,' bool Ready()const', ''' void ShadeBumperPositions(Oot3dNativeGame::NativeA32Memory& memory) {
  uint8_t pause=1,instrument=1;
  if(TouchHudActive.load() || JumpBumperFirst!=33 || JumpBumperCount!=64 ||
     !memory.Read8(PauseLayout,&pause) || !memory.Read8(OcarinaLayout,&instrument) || pause || instrument)return;
  std::array<float,64*12> positions{};
  const auto address=Positions+33*12*sizeof(float);
  if(!memory.ReadBytes(address,std::span(reinterpret_cast<uint8_t*>(positions.data()),sizeof(positions))))return;
  float minX=positions[0],maxX=minX,minY=positions[1],maxY=minY;
  for(unsigned i=0;i<64;++i)for(unsigned v=0;v<2;++v){
   const float x=positions[i*12+v*3],y=positions[i*12+v*3+1];
   if(!std::isfinite(x)||!std::isfinite(y))return;
   minX=std::min(minX,x);maxX=std::max(maxX,x);minY=std::min(minY,y);maxY=std::max(maxY,y);
  }
  if(maxX-minX<1 || maxY-minY<1)return;
  float templateMinX=400,templateMaxX=0,templateMinY=240,templateMaxY=0;
  for(const auto& quad:ManualJump_BumperPatches)for(unsigned v=0;v<4;++v){
   templateMinX=std::min(templateMinX,quad[v*2]);templateMaxX=std::max(templateMaxX,quad[v*2]);
   templateMinY=std::min(templateMinY,quad[v*2+1]);templateMaxY=std::max(templateMaxY,quad[v*2+1]);
  }
  for(unsigned i=0;i<64;++i)for(unsigned v=0;v<4;++v){
   positions[i*12+v*3]=minX+(ManualJump_BumperPatches[i][v*2]-templateMinX)*(maxX-minX)/(templateMaxX-templateMinX);
   positions[i*12+v*3+1]=minY+(ManualJump_BumperPatches[i][v*2+1]-templateMinY)*(maxY-minY)/(templateMaxY-templateMinY);
  }
  memory.WriteBytes(address,std::span(reinterpret_cast<const uint8_t*>(positions.data()),sizeof(positions)));
 }
 void ShadeBumperUVs(Oot3dNativeGame::NativeA32Memory& memory,uint32_t source,uint32_t size) {
  if(source!=UVs || JumpBumperFirst!=33 || JumpBumperCount!=64 || size<97*8*sizeof(float))return;
  memory.WriteBytes(UVs+33*8*sizeof(float),std::span(reinterpret_cast<const uint8_t*>(ManualJump_BumperUVs),sizeof(ManualJump_BumperUVs)));
 }
 bool Ready()const''')
    patch(header,'if(NativeTouchHud.Ready())return {NativeTouchHud.Upload,NativeTouchHud.PrepareAction};',
          'if(NativeTouchHud.Ready())return {NativeTouchHud.Upload,NativeTouchHud.PrepareAction,0x00317D1Cu};')
    patch(header,' if(NativeTouchHud.Ready())return',
          ' NativeTouchHud.ActionContextPointer=root["reframed_frontend"].value("context_pointer",0u);\n if(NativeTouchHud.Ready())return')
    clean=Path(__file__).with_name('clean_action_preview.inc').read_text()
    patch(header,' bool Ready()const',clean+' bool Ready()const')
    patch(header,'  HaveAction=false;\n  if(!Gameplay(memory))return;',
          '  PlaceCleanAction(memory);\n  HaveAction=false;\n  if(!Gameplay(memory))return;')
    frame=engine/BASE/'oot3d_native_a32_window_frame.cpp'
    patch(frame,'if(RetunedFrontend::TouchHudActive.load()&&RetunedFrontend::TouchHudLive.load()) {',
          'if((RetunedFrontend::TouchHudActive.load()&&RetunedFrontend::TouchHudLive.load())||RetunedFrontend::NativeTouchHud.HaveCleanAction) {')
    patch(frame,'auto icons=RetunedFrontend::NativeTouchHud.Overlay(process.Memory(),*atlas,actionAtlas?&*actionAtlas:nullptr);',
          'auto icons=RetunedFrontend::NativeTouchHud.Overlay(process.Memory(),*atlas,actionAtlas?&*actionAtlas:nullptr);\n      auto clean=RetunedFrontend::NativeTouchHud.CleanActionOverlay(process.Memory(),*atlas,actionAtlas?&*actionAtlas:nullptr);\n      icons.insert(icons.end(),clean.begin(),clean.end());')
    candidate=engine/BASE/'oot3d_native_a32_candidate_dispatch.cpp'
    patch(candidate,'  auto& touchHud=RetunedFrontend::NativeTouchHud;',
          '  auto& touchHud=RetunedFrontend::NativeTouchHud;\n  if(pc==0x00317D1Cu && dispatch.Memory)touchHud.ShadeBumperUVs(*dispatch.Memory,state.r[2],state.r[1]);')
    patch(candidate,'(pc==touchHud.Upload||pc==touchHud.PrepareAction)',
          '(pc==touchHud.Upload||pc==touchHud.PrepareAction||pc==0x00317D1Cu)')
    patch(candidate,'touchHud.PlaceLegacyDpad(*dispatch.Memory);touchHud.PlaceItems(*dispatch.Memory);',
          'touchHud.PlaceLegacyDpad(*dispatch.Memory);touchHud.ShadeBumperPositions(*dispatch.Memory);touchHud.PlaceItems(*dispatch.Memory);')

if __name__=='__main__':
    import sys
    install(Path(sys.argv[1]).resolve())
