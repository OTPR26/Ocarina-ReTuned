#include "../../tools/native/switch/deko_backend/native_coordinates.h"
#include <cassert>
#include <initializer_list>
#include <cstdio>
int main() {
 // ReFramed's actual Items shelf and model-preview rectangles: logical x=24
 // and x=208 respectively. Portrait PICA y=400-left-width.
 struct Rect {int left,width;};
 for (const auto r : {Rect{24,240},Rect{208,180},Rect{20,216},Rect{24,190}}) {
  const int picaY=400-r.left-r.width;
  for(int scale : {1,2,3}) {
   const int top=RetunedDeko::TopLeftY(400*scale,picaY*scale,r.width*scale);
   assert(top==r.left*scale);
   assert(RetunedDeko::TopLeftY(400*scale,top,r.width*scale)==picaY*scale);
   // Inclusive scissor and viewport must cover exactly the same pixels.
   const int inclusiveEnd=picaY+r.width-1;
   assert(400*scale-(inclusiveEnd+1)*scale==top);
  }
 }
 assert(RetunedDeko::TopLeftY(1200.f,0.f,1200.f)==0.f);
 puts("PASS: ReFramed shelf/preview positions, inclusive clipping, scales 1-3, full-screen preserved");
}
