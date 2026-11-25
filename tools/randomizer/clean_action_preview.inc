 uint32_t ActionContextPointer=0;
 bool ActionGameplay(Oot3dNativeGame::NativeA32Memory& memory)const {
  uint32_t context=0,pause=0;uint8_t type=0,subtype=0;
  return ActionContextPointer && memory.Read32(ActionContextPointer,&context) && context &&
   memory.Read8(context+0x100,&type) && type==3 &&
   memory.Read8(context+0x101,&subtype) && subtype==2 &&
   memory.Read32(0x0050af68,&pause) && pause==2;
 }
 bool HaveCleanAction=false,HaveCleanActionText=false;
 std::array<float,12> CleanActionPositions{},CleanActionTextPositions{};
 std::array<float,8> CleanActionTextUVs{};
 std::array<float,4> CleanActionTextColor{1,1,1,1};
 float CleanActionAlpha=1.f;
 void PlaceCleanAction(Oot3dNativeGame::NativeA32Memory& memory) {
  HaveCleanAction=false;HaveCleanActionText=false;
  uint8_t pause=1,instrument=1;
  if(!ActionGameplay(memory) || TouchHudActive.load() || !Ready() ||
     !memory.Read8(PauseLayout,&pause)||!memory.Read8(OcarinaLayout,&instrument)||pause||instrument)return;
  uint32_t source=0,board=0,uvAddress=0,colorAddress=0;
  if(!memory.Read32(ActionSource,&source)||!source||!ActionOwner||!memory.Read32(ActionOwner,&board)||!board||
     !memory.Read32(board+0x14,&uvAddress)||!uvAddress||!memory.Read32(board+0x18,&colorAddress)||!colorAddress)return;
  std::array<float,24> positions{};std::array<float,16> uvs{};std::array<float,32> colors{};
  if(!memory.ReadBytes(source,std::span(reinterpret_cast<uint8_t*>(positions.data()),sizeof(positions)))||
     !memory.ReadBytes(uvAddress,std::span(reinterpret_cast<uint8_t*>(uvs.data()),sizeof(uvs)))||
     !memory.ReadBytes(colorAddress,std::span(reinterpret_cast<uint8_t*>(colors.data()),sizeof(colors))))return;
  for(unsigned q=0;q<2;++q){
   auto* p=positions.data()+q*12;
   float minX=p[0],maxX=p[0],minY=p[1],maxY=p[1];
   for(unsigned v=1;v<4;++v){minX=std::min(minX,p[v*3]);maxX=std::max(maxX,p[v*3]);minY=std::min(minY,p[v*3+1]);maxY=std::max(maxY,p[v*3+1]);}
   const float w=maxX-minX,h=maxY-minY;
   if(w<1 || h<1)continue;
   if(w<=h*1.35f&&h<=w*1.35f){
    std::copy_n(p,12,CleanActionPositions.begin());CleanActionAlpha=colors[q*16+3];HaveCleanAction=true;
   }else{
    std::copy_n(p,12,CleanActionTextPositions.begin());std::copy_n(uvs.data()+q*8,8,CleanActionTextUVs.begin());
    std::copy_n(colors.data()+q*16,4,CleanActionTextColor.begin());HaveCleanActionText=true;
   }
  }
  if(HaveCleanAction){
   std::fill(positions.begin(),positions.end(),0.f);
   memory.WriteBytes(source,std::span(reinterpret_cast<const uint8_t*>(positions.data()),sizeof(positions)));
  }else HaveCleanActionText=false;
 }
 std::vector<oot3d::ui::UiPrimitive> CleanActionOverlay(Oot3dNativeGame::NativeA32Memory& memory,const oot3d::ui::UiTextureIdentity& atlas,const oot3d::ui::UiTextureIdentity* actionAtlas)const {
  uint8_t pause=1,instrument=1;
  if(!ActionGameplay(memory)||!HaveCleanAction||TouchHudActive.load()||!memory.Read8(PauseLayout,&pause)||!memory.Read8(OcarinaLayout,&instrument)||pause||instrument)return {};
  std::array<float,8> uv{};
  if(!memory.ReadBytes(UVs+8*sizeof(float),std::span(reinterpret_cast<uint8_t*>(uv.data()),sizeof(uv))))return {};
  auto ordered=[](const auto& positions){
   std::array<unsigned,4> order{0,1,2,3};
   std::sort(order.begin(),order.end(),[&](unsigned a,unsigned b){return positions[a*3+1]==positions[b*3+1]?positions[a*3]<positions[b*3]:positions[a*3+1]<positions[b*3+1];});
   return order;
  };
  std::vector<oot3d::ui::UiPrimitive> result;
  oot3d::ui::UiPrimitive p;p.subsystem=oot3d::ui::UiSubsystem::GameplayHud;p.role=oot3d::ui::UiPrimitiveRole::ActionButton;
  p.texture=atlas;p.layer=12;p.color.alpha=CleanActionAlpha;
  std::array<oot3d::ui::UiVertex,4> corners{};const auto order=ordered(CleanActionPositions);
  for(unsigned i=0;i<4;++i){const auto v=order[i],t=(i+2)%4;const auto point=TouchHudWindowPoint(CleanActionPositions[v*3],CleanActionPositions[v*3+1],TouchHudAspect.load());corners[i]={point[0],point[1],uv[t*2],1-uv[t*2+1]};}
  p.corners=corners;p.destination={corners[0].x,corners[0].y,corners[1].x-corners[0].x,corners[2].y-corners[0].y};result.push_back(p);
  if(HaveCleanActionText&&actionAtlas){
   p.texture=*actionAtlas;p.layer=13;p.color={CleanActionTextColor[0],CleanActionTextColor[1],CleanActionTextColor[2],CleanActionTextColor[3]};
   const auto textOrder=ordered(CleanActionTextPositions);
   for(unsigned i=0;i<4;++i){const auto v=textOrder[i];const auto point=TouchHudWindowPoint(CleanActionTextPositions[v*3],CleanActionTextPositions[v*3+1],TouchHudAspect.load());corners[i]={point[0],point[1],CleanActionTextUVs[v*2],1-CleanActionTextUVs[v*2+1]};}
   p.corners=corners;p.destination={corners[0].x,corners[0].y,corners[1].x-corners[0].x,corners[2].y-corners[0].y};result.push_back(p);
  }
  return result;
 }
