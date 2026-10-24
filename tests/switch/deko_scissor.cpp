#include "../../tools/native/switch/deko_backend/scissor.h"
#include <cassert>
int main(){
 constexpr int w=7,h=5;
 for(int x0=-1;x0<=w+1;x0++)for(int x1=-1;x1<=w+1;x1++)
 for(int y0=-1;y0<=h+1;y0++)for(int y1=-1;y1<=h+1;y1++){
  int coverage[h][w]{};
  auto rects=RetunedDeko::ExcludeRect(w,h,x0,y0,x1,y1);
  assert(rects.size()<=4);
  for(auto r:rects){assert(r.x>=0&&r.y>=0&&r.x+r.width<=w&&r.y+r.height<=h);
   for(int y=r.y;y<r.y+r.height;y++)for(int x=r.x;x<r.x+r.width;x++)coverage[y][x]++;
  }
  for(int y=0;y<h;y++)for(int x=0;x<w;x++){
   bool excluded=x>=x0&&x<x1&&y>=y0&&y<y1;
   assert(coverage[y][x]==(excluded?0:1));
  }
 }
}
