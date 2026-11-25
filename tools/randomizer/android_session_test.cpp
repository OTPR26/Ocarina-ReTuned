#include "android_session.h"
#include <cassert>
#include <thread>
int main() {
    RetunedRandomizer::AndroidSessionQueue queue;
    assert(!queue.Pending() && !queue.Take());
    assert(!queue.Queue({},0,false));
    assert(!queue.Queue({"--game"},3,false));
    assert(!queue.Queue({"--game"},-1,true));
    std::thread frontend([&]{assert(queue.Queue({"--manifest","seed-one"},0,true));});
    frontend.join();
    assert(queue.Pending());
    assert(!queue.Queue({"--manifest","seed-two"},1,true));
    auto first=queue.Take();
    assert(first && first->randomizerSlot==0 && first->newGame && first->arguments[1]=="seed-one");
    assert(!queue.Pending() && !queue.Take());
    assert(queue.Queue({"--manifest","normal"},-1,false));
    auto normal=queue.Take();
    assert(normal && normal->randomizerSlot==-1 && !normal->newGame && normal->arguments[1]=="normal");
}
