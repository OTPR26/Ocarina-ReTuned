#include "../tools/frontend/television_remote.h"
#include "../tools/frontend/menu_navigation.h"
#include <cassert>
#include <limits>
int main() {
 using namespace RetunedFrontend;
 auto input=RemoteButtons(0,-1,true,false);
 assert(input.Down&&!input.Accept); // Clicking a direction must not also activate the selected item.
 input=RemoteButtons(0,0,true,false);assert(input.Accept);
 input=RemoteButtons(-1,0,false,true);assert(input.Left&&input.Back);
 input=RemoteButtons(std::numeric_limits<float>::quiet_NaN(),0,false,false);assert(!input.Left&&!input.Right);
 int previous=-1;unsigned last=0;
 assert(RefreshMenuGamepads(0,previous,1,last,false));
 assert(!RefreshMenuGamepads(0,previous,300,last,false));
 assert(RefreshMenuGamepads(1,previous,301,last,false));
 assert(!RefreshMenuGamepads(1,previous,302,last,true));
 assert(RefreshMenuGamepads(1,previous,551,last,false)); // Recover a missed hotplug notification.
 assert(!RefreshMenuGamepads(1,previous,552,last,false));
 assert(RefreshMenuGamepads(0,previous,553,last,false));
}
