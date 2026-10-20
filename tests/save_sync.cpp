#include "../tools/native/apple/save_sync_policy.h"
#include <cassert>
int main() {
 using namespace RetunedSaveSync;
 assert(Decide("","","")==Action::None);
 assert(Decide("a","","")==Action::Upload);
 assert(Decide("","a","")==Action::Download);
 assert(Decide("a","a","")==Action::None);
 assert(Decide("a","b","")==Action::Conflict);
 assert(Decide("a","b","a")==Action::Download);
 assert(Decide("b","a","a")==Action::Upload);
 assert(Decide("b","c","a")==Action::Conflict);
 assert(Decide("","a","a")==Action::Download);
 assert(Decide("a","","a")==Action::Conflict);
 assert(SaveName("save00.bin") && SaveName("save05.bin") && SaveName("system.dat"));
 assert(!SaveName("../save00.bin") && !SaveName("save06.bin") && !SaveName("config.json"));
}
