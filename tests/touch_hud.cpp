#include "../tools/frontend/touch_hud_model.h"
#include <cassert>
#include "../tools/frontend/touch_hud_state.h"
int main(){
 using namespace RetunedFrontend;
 SetTouchHudDisplay(956,440);
 assert(std::abs(TouchHudAspect.load()-2868.f/1320.f)<.00001f);
 SetTouchHudDisplay(1280,0);assert(std::abs(TouchHudAspect.load()-956.f/440.f)<.00001f);
 TouchHudAnchors anchors;for(unsigned i=0;i<8;++i)anchors[i]={.1f+i*.1f,.55f,true};
 std::array<float,33*12> geometry{};
 for(unsigned q=0;q<33;++q)for(unsigned v=0;v<4;++v){geometry[q*12+v*3]=q*2+(v%2)*12;geometry[q*12+v*3+1]=q*3+(v/2)*14;geometry[q*12+v*3+2]=7;}
 const auto original=geometry;
 auto invalid=anchors;invalid[4].Valid=false;assert(!PlaceTouchHud(geometry,invalid)&&geometry==original);
 assert(PlaceTouchHud(geometry,anchors));
 assert(geometry[13*12]==original[13*12]); // Vitals unchanged.
 assert(geometry[24*12]==original[24*12]); // Currency unchanged.
 for(const auto [quad,slot]:std::array{std::pair{5u,1u},std::pair{6u,2u},std::pair{7u,3u},std::pair{9u,4u},std::pair{11u,5u},std::pair{10u,6u},std::pair{8u,7u}}){
  const auto c=HudQuadCenter(geometry,quad);assert(std::abs(c[0]-anchors[slot].X*400)<.001f);assert(std::abs(c[1]-anchors[slot].Y*240)<.001f);
  assert(geometry[quad*12+3]-geometry[quad*12]==12);assert(geometry[quad*12+7]-geometry[quad*12+1]==14);assert(geometry[quad*12+2]==7);
 }
 // A west touch arm outside the legacy HUD must survive in the window overlay.
 const float phoneAspect=2868.f/1320.f;
 const TouchHudAnchor west{.05f,.7f,true};
 const auto nativeWest=TouchHudPoint(west,phoneAspect);
 assert(nativeWest[0]<0.f);
 const auto windowWest=TouchHudWindowPoint(nativeWest[0],nativeWest[1],phoneAspect);
 assert(std::abs(windowWest[0]-20.f)<.0001f&&std::abs(windowWest[1]-168.f)<.0001f);
 assert(TouchIconOpacity.load()==1.f);
 // Ammo retains its exact offset relative to the item it belongs to.
 assert(std::abs((geometry[28*12]-geometry[6*12])-(original[28*12]-original[6*12]))<.001f);
 std::array<float,24> action{0,16,0,16,16,0,0,0,0,16,0,0, -20,22,0,20,22,0,-20,17,0,20,17,0};
 const auto old=action;assert(PlaceTouchAction(action,anchors[0]));
 assert(std::abs(HudQuadCenter(action,1)[0]-40)<.001f);
 assert(action[3]==action[0]&&action[7]==action[1]); // No extra A circle.
 assert(action[15]-action[12]==old[15]-old[12]); // Verb size unchanged.
 // A long action verb may cross the legacy right edge but fits the full window.
 auto rightAction=old;
 const TouchHudAnchor rightButton{.9f,.7f,true};
 assert(PlaceTouchAction(rightAction,rightButton,phoneAspect));
 assert(rightAction[15]>400.f);
 const auto rightEdge=TouchHudWindowPoint(rightAction[15],rightAction[16],phoneAspect);
 assert(rightEdge[0]<400.f);
 const auto actionCenter=HudQuadCenter(rightAction,1);
 const auto windowCenter=TouchHudWindowPoint(actionCenter[0],actionCenter[1],phoneAspect);
 assert(std::abs(windowCenter[0]-360.f)<.001f);
 // Round-trip real full-window anchors through the aspect-preserving HUD
 // projection. Wide phones previously pulled both groups toward the center.
 for(float aspect:{2868.f/1320.f,16.f/9.f,4.f/3.f}) {
  auto placed=original;assert(PlaceTouchHud(placed,anchors,aspect));
  const float canvasWidth=std::max(400.f,240.f*aspect),canvasHeight=std::max(240.f,400.f/aspect);
  for(const auto [quad,slot]:std::array{std::pair{9u,4u},std::pair{6u,2u}}){
   const auto c=HudQuadCenter(placed,quad);
   assert(std::abs((c[0]-200)/canvasWidth+.5f-anchors[slot].X)<.00001f);
   assert(std::abs((c[1]-120)/canvasHeight+.5f-anchors[slot].Y)<.00001f);
  }
  auto a=old;assert(PlaceTouchAction(a,anchors[0],aspect));
  const auto c=HudQuadCenter(a,1);assert(std::abs((c[0]-200)/canvasWidth+.5f-anchors[0].X)<.00001f);
 }
}
