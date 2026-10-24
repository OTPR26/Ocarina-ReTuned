#include "tools/native/switch/deko_backend/scissor.h"
#include <cassert>
int main(){
 using RetunedDeko::GuiClip;
 // Child-page content must align with projected vertices, independently of
 // an external SDL context's reported framebuffer scale.
 auto r=GuiClip(1280,720,0,0,1280,720,400,100,1260,650);
 assert(r.x==400&&r.y==100&&r.width==860&&r.height==550);
 r=GuiClip(1280,720,20,40,2560,1440,820,240,2540,1340);
 assert(r.x==400&&r.y==100&&r.width==860&&r.height==550);
 r=GuiClip(1280,720,0,0,1280,720,-10,-20,1300,740);
 assert(r.x==0&&r.y==0&&r.width==1280&&r.height==720);
 r=GuiClip(1280,720,0,0,1280,720,1300,740,1500,900);
 assert(r.width==0&&r.height==0);
 r=GuiClip(1280,720,0,0,0,720,0,0,100,100);
 assert(r.width==0&&r.height==0);
}
