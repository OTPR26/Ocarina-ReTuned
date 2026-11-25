#include "continue_game.h"
#include <cassert>
#include <map>
struct Memory {
    std::map<std::uint32_t,std::uint32_t> data{{0x504fb0,3},{0x55bea8,1},{0x42f9a8,0xe92d4ff0},{0x44737c,0xe92d47f0}};
    int writes=0;
    bool Read32(std::uint32_t p,std::uint32_t* v) {auto it=data.find(p);if(it==data.end())return false;*v=it->second;return true;}
    bool Write32(std::uint32_t p,std::uint32_t v) {data[p]=v;++writes;return true;}
};
int main() {
    Memory m;
    RetunedRandomizer::ContinueGame off(false);
    assert(!off.Update(0x42f9a8,m) && m.writes==0);
    RetunedRandomizer::ContinueGame run(true);
    assert(!run.Update(0x42f9ac,m) && m.writes==0);
    for(auto phase:{0,1,2,4,8,10}) {m.data[0x504fb0]=phase;assert(!run.Update(0x42f9a8,m));}
    assert(m.writes==0);
    m.data[0x504fb0]=3;
    assert(run.Update(0x42f9a8,m));
    assert(m.data[0x504fb4]==0 && m.data[0x504fc8]==0 && m.data[0x504fb0]==4);
    for(auto phase:{4,7}) {m.data[0x504fb0]=phase;assert(!run.Update(0x42f9a8,m));}
    m.data[0x504fb0]=8;
    assert(run.Update(0x42f9a8,m));
    assert(m.data[0x504fb0]==10 && m.data[0x504fb8]==0);
    m.data[0x504fb0]=3;
    assert(!run.Update(0x42f9a8,m));
    // Completing one session must not suppress Continue in the next one.
    Memory nextMemory;
    RetunedRandomizer::ContinueGame nextRun(true);
    assert(nextRun.Update(0x42f9a8,nextMemory));
    Memory ordinaryMemory;
    RetunedRandomizer::ContinueGame ordinary(false);
    assert(!ordinary.Update(0x42f9a8,ordinaryMemory) && ordinaryMemory.writes==0);
    Memory fresh; fresh.data[0x55bea8]=0;
    RetunedRandomizer::ContinueGame create(true,true);
    assert(create.Update(0x42f9a8,fresh));
    assert(fresh.data[0x504fb0]==5 && fresh.data[0x504fb4]==0);
    assert(fresh.data[0x55b610]==0xc2a00000 && fresh.data[0x55b61c]==0);
    assert(!create.Update(0x42f9a8,fresh));
    fresh.data[0x504fb0]=3;
    assert(!create.Update(0x42f9a8,fresh));
    fresh.data[0x55bea8]=1;
    assert(create.Update(0x42f9a8,fresh));
    assert(fresh.data[0x504fb0]==4);
    fresh.data[0x504fb0]=7;
    assert(!create.Update(0x42f9a8,fresh));
    fresh.data[0x504fb0]=8;
    assert(create.Update(0x42f9a8,fresh));
    assert(fresh.data[0x504fb0]==10 && fresh.data[0x504fb8]==0);
    fresh.data[0x504fb0]=3;
    assert(!create.Update(0x42f9a8,fresh));
    Memory occupied; RetunedRandomizer::ContinueGame refuse(true,true);
    bool refused=false;
    try {refuse.Update(0x42f9a8,occupied);} catch(const std::runtime_error&) {refused=true;}
    assert(refused && occupied.writes==0);
    for(auto address:{0x55bea8u,0x42f9a8u,0x44737cu}) {
        Memory bad;bad.data[address]=0;RetunedRandomizer::ContinueGame rejected(true);
        bool threw=false;try{rejected.Update(0x42f9a8,bad);}catch(const std::runtime_error&){threw=true;}
        assert(threw && bad.writes==0);
    }
}
