#include "../tools/frontend/game_save.h"
#include "../tools/frontend/settings_button.h"
#include "../tools/frontend/native_save_menu.h"
#include <map>
#include <cassert>
int main() {
 using namespace RetunedFrontend;
 GameSaveShortcut save;
 assert(!save.Request());
 save.SetAvailable(true);
 // The physical shortcut still opens Settings and is stripped from guest input.
 bool held=false;unsigned buttons=8;
 assert(RouteSettingsButton(buttons,8,held,false)&&buttons==0);
 // A General-page request waits for Settings to close, then bypasses that shortcut.
 assert(save.Request());
 assert(!save.Take(true,true,true)&&save.Pending()&&!save.Visible());
 assert(save.Take(true,true,false)&&save.Visible());
 buttons|=8;assert(buttons==8);
 assert(!save.Take(true,true,false)); // One tap never opens and immediately closes Save.
 assert(save.Request());assert(!save.Take(false,true,false));
 assert(!save.Pending()&&!save.Visible()); // Mode changes cannot leave a deferred Save.
 assert(save.Request());assert(!save.Take(true,false,false)&&!save.Pending());
 save.SetAvailable(false);assert(!save.Request());
 save.SetAvailable(true);assert(save.Request());save.SetAvailable(false);
 assert(!save.Pending()&&!save.Visible()); // Death, a cutscene, or a pause transition cancels it.
 save.SetDialog(true);
 assert(!save.ConsumeDialogTouch(30,150,true)); // Keep native Save/Don't Save touches.
 assert(save.ConsumeDialogTouch(160,220,true)&&!save.BackInput(true)); // Removed Options is inert.
 assert(save.ConsumeDialogTouch(30,220,true));
 assert(!save.BackInput(false)); // Rendering alone must not consume the tap.
 for(int i=0;i<6;++i)assert(save.BackInput(true));
 assert(!save.BackInput(true));
 save.RequestBack();save.SetDialog(false);assert(!save.BackInput(true));
 assert(!LowerUiSettled(2,false,false)); // Wait through the native scene fade.
 assert(LowerUiSettled(2,true,false));
 assert(!LowerUiSettled(13,true,false)); // Gear's closing animation.
 assert(LowerUiSettled(12,true,false)&&LowerUiSettled(0,true,true));
 struct Memory {
  std::map<unsigned,unsigned> Data;
  bool Read32(unsigned a,unsigned* v){auto i=Data.find(a);if(i==Data.end())return false;*v=i->second;return true;}
  bool IsWritable(unsigned a,unsigned n){return a>=0x2000&&a+n<=0x2000+78*64;}
  bool Write32(unsigned a,unsigned v){if(!IsWritable(a,4))return false;Data[a]=v;return true;}
 } memory;
 memory.Data[0x0050A510]=0x1000;memory.Data[0x1000]=78;memory.Data[0x1018]=0x2000;
 for(unsigned i=0;i<78*64;i+=4)memory.Data[0x2000+i]=0x3f800000;
 assert(HideNativeSaveOptions(memory));
 for(unsigned i=0;i<78*64;i+=4) {
  bool options=i/64>=18&&i/64<=21&&i%16==12;
  assert(memory.Data[0x2000+i]==(options?0u:0x3f800000u));
 }
 auto before=memory.Data;memory.Data[0x1000]=77;
 assert(!HideNativeSaveOptions(memory));memory.Data[0x1000]=78;assert(memory.Data==before);
}
