// SPDX-License-Identifier: GPL-2.0-or-later
// Adapted from SariaUI's pinned host/runtime_tables.h; see NOTICE.md.
#pragma once
#include <bit>
#include <vector>
#include <stdexcept>
#include "entrance.hpp"
#include "shops.hpp"
#include "gold_skulltulas.hpp"
#include "music.hpp"
#include "sound_effects.hpp"
#include "ocarina_notes.hpp"

struct ArmBytes {
    std::vector<unsigned char> bytes;
    void u8(unsigned v){bytes.push_back(v);}
    void u16(unsigned v){u8(v);u8(v>>8);}
    void u32(std::uint32_t v){u16(v);u16(v>>16);}
    void f32(float v){u32(std::bit_cast<std::uint32_t>(v));}
    void align(unsigned n){while(bytes.size()%n)u8(0);}
};
template<class Put,class Patch> void RuntimeTables(Put put,Patch patch) {
    // Exact capacities from the pinned ARM ELF, checked again at image creation.
    const auto write=[&](const char* name,ArmBytes& b,std::size_t capacity){
        if(b.bytes.size()>capacity)throw std::runtime_error("Runtime table overflow");
        b.bytes.resize(capacity,0);put(name,b.bytes.data(),b.bytes.size());
    };
    ArmBytes entrances;
    for(const auto& e:entranceOverrides){entrances.u16(e.index);entrances.u16(e.destination);
        entrances.u16(e.blueWarp);entrances.u16(e.override);entrances.u16(e.overrideDestination);}
    write("rEntranceOverrides",entrances,0xa1e);
    ArmBytes enemies;std::vector<EnemyOverride> overrides;
    if(Settings::Enemizer)Enemizer::FillPatchOverrides(overrides);
    for(const auto& e:overrides){enemies.u32(e.key);enemies.u8(e.enemyId);enemies.u8(e.paramsIdx);enemies.u8(e.vanillaId);enemies.u8(0);}
    write("rEnemyOverrides",enemies,0x1900);
    ArmBytes skulls;
    for(const auto& g:*Gs_GetOverrideData()) {
        skulls.u8(g.arrayIndex);skulls.u8(g.bitFlag);skulls.u16(g.scene);skulls.u8(g.room);
        skulls.u8(g.ageCondition);skulls.u8(g.timeCondition);skulls.u8(0);
        skulls.f32(g.posRot.pos.x);skulls.f32(g.posRot.pos.y);skulls.f32(g.posRot.pos.z);
        skulls.u16(g.posRot.rot.x);skulls.u16(g.posRot.rot.y);skulls.u16(g.posRot.rot.z);skulls.u16(0);
    }
    write("rGsLocOverrides",skulls,0xaf0);
    ArmBytes music;
    for(unsigned i=0;i<128;++i)music.u32(i<Music::seqOverridesMusic.size()?Music::seqOverridesMusic[i]:Music::BGM_BASE+i);
    write("rBGMOverrides",music,0x200);
    ArmBytes sound;const auto& s=SFX::GetSFXData();
    for(auto v:s.rSeqCounts)sound.u16(v);
    for(auto v:s.rSeqTypesSFX)sound.u8(v);
    sound.align(4);
    for(auto v:s.rSFXOverrides_All)sound.u32(v);
    sound.u16(s.rSFXOverrides_TrimmedCount);sound.align(4);
    for(auto v:s.rSFXOverrides_AllTrimmed)sound.u32(v);
    for(const auto& group:s.rSFXOverrides_Types)for(auto v:group)sound.u32(v);
    write("rSfxData",sound,0x5b38);
    ArmBytes prices,texts;
    for(auto id:std::array<unsigned,11>{0x9014,0x900f,0x900a,0x9028,0x9032,0x9028,0x9046,0x9028,0x9028,0x9028,0x9028}) {
        unsigned price=0;
        if(Settings::Scrubsanity.Is(SCRUBSANITY_RANDOM_PRICES)){price=GetRandomScrubPrice();id=0x9000+price;}
        else if(Settings::Scrubsanity.Is(SCRUBSANITY_AFFORDABLE))id=0x900a;
        prices.u16(price);texts.u16(id);
    }
    write("rScrubRandomItemPrices",prices,0x16);
    if(Settings::Scrubsanity.IsNot(SCRUBSANITY_OFF))patch(0x52236c,texts.bytes.data(),texts.bytes.size());
    if(Settings::RandomSongNotes){
        patch(0x54c222,OcarinaNotes::SongData,sizeof(OcarinaNotes::SongData));
        patch(0x54c8b0,OcarinaNotes::FrogSongNotes,sizeof(OcarinaNotes::FrogSongNotes));
    }
}
