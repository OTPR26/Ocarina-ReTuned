#include <cassert>
#include <cmath>
#define __ANDROID__ 1
#include "../tools/frontend/interface_metrics.h"
int main() {
 using namespace RetunedFrontend;
 static_assert(MobileSettingsPlatform());
 // A capped render surface must still show 20 dp text on a high-density screen.
 AndroidDisplayDensity=3;AndroidDisplayHeight=1440;
 SetInterfacePixelRatio(1920,1920);
 assert(InterfaceFontPixels()==192.f); // Density must also size the atlas before the first frame.
 const float surfaceHeight=720;
 const float screenFontPixels=20*MenuScale(surfaceHeight)*1440/surfaceHeight;
 assert(std::abs(screenFontPixels/3-20)<.001f);
 MenuSize=1.25f;
 assert(std::abs(20*MenuScale(surfaceHeight)*2/3-25)<.001f);
 AndroidDisplayDensity=1;AndroidDisplayHeight=720;MenuSize=1;
 assert(MenuScale(720)==1);
 AndroidDisplayHeight=0;
 assert(std::isfinite(MenuScale(720)));
}
