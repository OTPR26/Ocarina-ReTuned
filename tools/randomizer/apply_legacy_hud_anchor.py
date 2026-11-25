from pathlib import Path
from apply_android_session import patch
from apply_host_services import BASE

def install(engine):
    header=engine/BASE/'retuned_touch_hud_runtime.h'
    candidate=engine/BASE/'oot3d_native_a32_candidate_dispatch.cpp'
    if 'touchHud.PlaceLegacyDpad(*dispatch.Memory);' in candidate.read_text():
        return
    patch(header,'#include <vector>','#include <vector>\n#include "legacy_hud_anchor.h"\n#include "ship/Context.h"\n#include "ship/config/Config.h"')
    patch(header,' bool Ready()const', ''' bool LegacyRandomizerAnchor=false;
 void PlaceLegacyDpad(Oot3dNativeGame::NativeA32Memory& memory) {
  uint8_t pause=1,instrument=1;
  if(!LegacyRandomizerAnchor || TouchHudActive.load() || !Ready() ||
     !memory.Read8(PauseLayout,&pause) || !memory.Read8(OcarinaLayout,&instrument) || pause || instrument)return;
  std::array<float,33*12> positions{};
  if(!memory.ReadBytes(Positions,std::span(reinterpret_cast<uint8_t*>(positions.data()),sizeof(positions))))return;
  const auto config=Ship::Context::GetRawInstance()->GetConfig()->GetNestedJson();
  const auto saved=config.value("Reframed",nlohmann::json::object());
  constexpr std::array<float,4> scales{0.f,.75f,1.f,1.25f};
  const int size=saved.value("hud_size",2),group=saved.value("dpad_size",100);
  if(size<0||size>3)return;
  if(!RetunedRandomizer::AnchorLegacyDpad(positions,scales[size],group/100.f,saved.value("hud_preset",0)==1))return;
  for(unsigned q:{4u,8u,9u,10u,11u,12u,23u})
   memory.WriteBytes(Positions+q*12*sizeof(float),std::span(reinterpret_cast<const uint8_t*>(positions.data()+q*12),12*sizeof(float)));
 }
 bool Ready()const''')
    patch(header,' if(NativeTouchHud.Ready())return', ''' NativeTouchHud.LegacyRandomizerAnchor=root.contains("randomizer_proof") &&
     !root["reframed_frontend"]["functions"].contains("NativeHud_SetGroupScale");
 if(NativeTouchHud.Ready())return''')
    candidate=engine/BASE/'oot3d_native_a32_candidate_dispatch.cpp'
    patch(candidate,'      if(state.r[0]!=0)touchHud.PlaceItems(*dispatch.Memory);',
          '      if(state.r[0]!=0){touchHud.PlaceLegacyDpad(*dispatch.Memory);touchHud.PlaceItems(*dispatch.Memory);}')

if __name__=='__main__':
    import sys
    install(Path(sys.argv[1]).resolve())
