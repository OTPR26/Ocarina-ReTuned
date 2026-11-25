#include "generator.h"
#include <bit>
#include <vector>
#include <mutex>
#include <stdexcept>
#include <nlohmann/json.hpp>
#include "hint_list.hpp"
#include "item_list.hpp"
#include "item_location.hpp"
#include "enemizer.hpp"
#include "settings.hpp"
#include "playthrough.hpp"
#include "random.hpp"
#include "fill.hpp"
#include "custom_messages.hpp"
#include "spoiler_log.hpp"
#include "hints.hpp"
#include "runtime_tables.h"

namespace RetunedRandomizer {
namespace {
std::mutex mutex;
const std::function<void(unsigned)>* callback = nullptr;
void Progress(unsigned attempt) { if(callback && *callback) (*callback)(attempt); }
std::string Hex(const void* data, std::size_t length) {
    static constexpr char digits[]="0123456789abcdef";
    const auto* bytes=static_cast<const unsigned char*>(data);
    std::string result;result.reserve(length*2);
    for(std::size_t i=0;i<length;++i) {result+=digits[bytes[i]>>4];result+=digits[bytes[i]&15];}
    return result;
}
}
std::string Generate(const std::string& seed, const std::function<void(unsigned)>& progress) {
    if(seed.empty() || seed.size()>128 || seed.find_first_of("\r\n\t")!=std::string::npos)
        throw std::invalid_argument("Seed must contain 1–128 bytes without tabs or newlines");
    static_assert(std::endian::native==std::endian::little);
    static_assert(sizeof(ItemOverride)==8);
    std::lock_guard lock(mutex);
    struct Reset {~Reset(){fillAttemptCallback=nullptr;callback=nullptr;}} reset;
    callback=&progress;fillAttemptCallback=Progress;
    static const bool initialized=[] {
        HintTable_Init(); ItemTable_Init(); LocationTable_Init();
        Enemizer::InitEnemyTypes(); Settings::InitSettings();
        return true;
    }();
    (void)initialized;
    Settings::SetDefaultSettings();
    Settings::SetDefaultSettings(true);
    using namespace Settings;
    Settings::seed=seed;
    Settings::Logic.SetSelectedIndex(LOGIC_GLITCHLESS);
    StartingAge.SetSelectedIndex(AGE_CHILD);
    SetDungeonTypes.SetSelectedIndex(OFF);MQDungeonCount.SetSelectedIndex(0);
    Settings::MirrorWorld.SetSelectedIndex(MIRRORWORLD_OFF);
    ShuffleEntrances.SetSelectedIndex(OFF);
    Shopsanity.SetSelectedIndex(SHOPSANITY_OFF);
    ShuffleSongs.SetSelectedIndex(0);
    ShuffleRewards.SetSelectedIndex(REWARDSHUFFLE_END_OF_DUNGEON);
    MapsAndCompasses.SetSelectedIndex(1);Keysanity.SetSelectedIndex(1);
    BossKeysanity.SetSelectedIndex(1);GanonsBossKey.SetSelectedIndex(1);
    GenerateSpoilerLog.SetSelectedIndex(OFF);
    FreeCamControl.SetSelectedIndex(0);QuickText.SetSelectedIndex(QUICKTEXT_VANILLA);
    CustomMessages::SetHostPriceMultiplier(1);
    if(!ValidateSettings())throw std::runtime_error("Invalid fixed proof preset");
    if(Playthrough::Playthrough_Init(StableSeedHash(seed))!=1)
        throw std::runtime_error("Generator could not find a beatable placement");
    nlohmann::ordered_json result;
    result["format"]="retuned-seed-proof-v1";
    result["generator_revision"]="40703bf55b05ab2dda0933a5c5007730b05cebe2";
    result["upstream_revision"]="d695cf5ad78dc1990da200af601b054860d707b8";
    result["preset"]="original-glitchless-proof-v1";
    result["seed"]=seed;
    result["runtime_ready"]=false;
    result["items"]=nlohmann::ordered_json::array();
    std::uint32_t previous=0;
    for(const auto& item:overrides) {
        if(!item.key.all || item.key.all<=previous)throw std::runtime_error("Invalid item key order");
        previous=item.key.all;
        result["items"].push_back({{"key",item.key.all},{"scene",item.key.scene},{"type",item.key.type},
            {"flag",item.key.flag},{"item",item.value.itemId},{"player",item.value.player},{"appearance",item.value.looksLikeItemId}});
    }
    if(overrides.empty() || overrides.size()>=ITEM_OVERRIDES_MAX)throw std::runtime_error("Invalid item count");
    const auto settings=FillContext();
    result["settings_le_hex"]=Hex(&settings,sizeof(settings));
    result["dungeon_rewards"]=rDungeonRewardOverrides;
    auto& fields=result["runtime_fields_hex"];
    const std::vector<ItemOverride> items(overrides.begin(),overrides.end());
    fields["rItemOverrides"]=Hex(items.data(),items.size()*sizeof(ItemOverride));
    fields["gSettingsContext"]=Hex(&settings,sizeof(settings));
    fields["rDungeonRewardOverrides"]=Hex(rDungeonRewardOverrides.data(),sizeof(rDungeonRewardOverrides));
    const std::array<std::int32_t,32> shopPrices{};
    fields["rShopsanityPrices"]=Hex(shopPrices.data(),sizeof(shopPrices));
    fields["gSpoilerData"]=Hex(GetSpoilerData(),sizeof(SpoilerData));
    // The guest uses short enums; host enum widths cannot be copied directly.
    std::vector<unsigned char> locations;
    const auto half=[&](unsigned value) {locations.push_back(value);locations.push_back(value>>8);};
    for(unsigned i=0;i<SPOILER_LOCDATS;++i) {
        const auto& block=*GetSpoilerDataLocs(i);
        for(const auto& item:block.ItemLocations) {
            half(item.LocationStrOffset);half(item.ItemStrOffset);
            locations.insert(locations.end(),{
                static_cast<unsigned char>(item.CollectionCheckType),item.LocationScene,item.LocationFlag,
                static_cast<unsigned char>(item.Group),static_cast<unsigned char>(item.CollectType),
                static_cast<unsigned char>(item.RevealType)});
        }
        locations.insert(locations.end(),block.StringData,block.StringData+SPOILER_STRING_DATA_SIZE);
    }
    fields["gSpoilerDataLocs"]=Hex(locations.data(),locations.size());
    std::array<unsigned char,10> importance{};
    for(unsigned i=0;i<importance.size();++i)importance[i]=static_cast<unsigned char>(dungeonImportance[i]);
    fields["rDungeonImportance"]=Hex(importance.data(),importance.size());
    result["native_patches"]=nlohmann::ordered_json::array();
    RuntimeTables([&](const char* name,const void* data,std::size_t size){fields[name]=Hex(data,size);},
        [&](unsigned address,const void* data,std::size_t size){
            result["native_patches"].push_back({{"address",address},{"data_hex",Hex(data,size)}});
        });
    const auto messages=CustomMessages::RawMessageData();
    const auto entries=CustomMessages::RawMessageEntryData();
    result["message_data_hex"]=Hex(messages.first,messages.second);
    result["message_entries_hex"]=Hex(entries.first,entries.second);
    result["spoiler"]=nlohmann::ordered_json::array();
    for(auto key:allLocations) {
        const auto* location=Location(key);
        result["spoiler"].push_back({{"location",location->GetName()}, {"item",location->GetPlacedItemName().GetNAEnglish()}});
    }
    return result.dump(2)+"\n";
}
}
