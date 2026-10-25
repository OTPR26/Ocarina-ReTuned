#include "../tools/native/android/dual_screen/lower_resolution.h"
#include <cassert>
int main() {
 using RetunedFrontend::AndroidLowerRenderExtent;
 // Thor: 4:3 lower image fits 1240x930 inside the 1240x1080 panel.
 const auto single=AndroidLowerRenderExtent(240,320,1240,1080);
 const auto doubled=AndroidLowerRenderExtent(480,320,1240,1080);
 assert(single && doubled);
 assert(single->Width==930 && single->Height==1240);
 assert(doubled->Width/2==single->Width && doubled->Height==single->Height);
 // A 16:9 external panel letterboxes the same native 4:3 content.
 const auto wide=AndroidLowerRenderExtent(240,320,1920,1080);
 assert(wide && wide->Width==1080 && wide->Height==1440);
 // Do not reinterpret scene or unrelated offscreen render targets.
 assert(!AndroidLowerRenderExtent(480,400,1240,1080));
 assert(!AndroidLowerRenderExtent(256,256,1240,1080));
 assert(!AndroidLowerRenderExtent(240,320,0,1080));
 assert(!AndroidLowerRenderExtent(240,320,1240,0));
}
