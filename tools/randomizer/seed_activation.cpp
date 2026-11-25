#include "seed_activation.h"
#include <map>

namespace RetunedRandomizer {
namespace {
using Json = nlohmann::json;
constexpr std::array fields{"rItemOverrides", "gSettingsContext", "rDungeonRewardOverrides",
    "rShopsanityPrices", "gSpoilerData", "gSpoilerDataLocs", "rDungeonImportance",
    "rEntranceOverrides", "rEnemyOverrides", "rGsLocOverrides", "rBGMOverrides",
    "rSfxData", "rScrubRandomItemPrices"};
void Require(bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); }
std::vector<std::uint8_t> Decode(const Json& value, std::size_t limit) {
    const auto& hex = value.get_ref<const std::string&>();
    Require(hex.size() % 2 == 0 && hex.size()/2 <= limit, "Invalid seed table size");
    auto digit=[](char c)->unsigned {
        if (c >= '0' && c <= '9') return c-'0';
        if (c >= 'a' && c <= 'f') return c-'a'+10;
        if (c >= 'A' && c <= 'F') return c-'A'+10;
        throw std::runtime_error("Invalid seed table encoding");
    };
    std::vector<std::uint8_t> out; out.reserve(hex.size()/2);
    for (std::size_t i=0; i<hex.size(); i+=2) out.push_back(digit(hex[i])*16+digit(hex[i+1]));
    return out;
}
std::uint32_t Read32(const std::vector<std::uint8_t>& bytes, std::size_t at) {
    std::uint32_t value=0;
    for (unsigned i=0;i<4;++i) value |= std::uint32_t(bytes.at(at+i)) << (i*8);
    return value;
}
void Write32(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint32_t value) {
    for (unsigned i=0;i<4;++i) bytes.at(at+i)=value>>(i*8);
}
}
std::vector<SeedWrite> PlanSeedActivation(const Json& seed, const Json& layout) {
    Require(seed.at("format")=="retuned-seed-proof-v1" && seed.at("runtime_ready")==false &&
        seed.at("preset")=="original-glitchless-proof-v1" &&
        seed.at("upstream_revision")=="d695cf5ad78dc1990da200af601b054860d707b8" &&
        seed.at("generator_revision")=="40703bf55b05ab2dda0933a5c5007730b05cebe2" &&
        layout.at("schema")==1, "Unsupported randomizer seed or layout");
    const auto& tables=seed.at("runtime_fields_hex");
    Require(tables.is_object() && tables.size()==fields.size(), "Unexpected seed tables");
    std::vector<SeedWrite> writes;
    auto range=[&](const char* name) {
        const auto& item=layout.at("symbols").at(name);
        const auto address=item.at(0).get<std::uint64_t>();
        const auto size=item.at(1).get<std::uint64_t>();
        Require(address>=0x680000 && address<0x800000 && size && size<=0x800000-address,
                "Invalid runtime seed range");
        return std::pair{static_cast<std::uint32_t>(address),static_cast<std::size_t>(size)};
    };
    for (const auto* name:fields) {
        const auto [address,size]=range(name);
        auto bytes=Decode(tables.at(name),size);
        if (std::string_view(name)=="rItemOverrides") {
            Require(!bytes.empty() && bytes.size()%8==0 && bytes.size()+8<=size,
                    "Item overrides need a terminating record");
            std::uint32_t previous=0;
            for (std::size_t at=0;at<bytes.size();at+=8) {
                auto key=Read32(bytes,at); Require(key>previous,"Invalid item override ordering"); previous=key;
            }
        } else Require(bytes.size()==size,"Seed table does not match runtime ABI");
        bytes.resize(size,0); writes.push_back({address,std::move(bytes)});
    }
    const auto [messageBase,capacity]=range("rCustomMessages");
    auto messages=Decode(seed.at("message_data_hex"),capacity);
    auto entries=Decode(seed.at("message_entries_hex"),capacity);
    Require(!entries.empty() && entries.size()%0x60==0,"Invalid message entries");
    const auto entryOffset=((messageBase+messages.size()+3)&~std::size_t(3))-messageBase;
    Require(entryOffset<=capacity && entries.size()<=capacity-entryOffset,"Seed messages exceed reservation");
    std::uint32_t previous=0; bool first=true;
    for (std::size_t at=0;at<entries.size();at+=0x60) {
        const auto id=Read32(entries,at);
        Require(first || id>previous,"Invalid message ordering"); first=false;previous=id;
        for (unsigned language=0;language<10;++language) {
            const auto pos=at+16+language*8;
            const auto start=Read32(entries,pos),length=Read32(entries,pos+4);
            if (length) {
                Require(start<=messages.size() && length<=messages.size()-start,"Message exceeds seed data");
                Write32(entries,pos,messageBase+start);
            } else Write32(entries,pos,0);
        }
    }
    messages.resize(entryOffset,0); messages.insert(messages.end(),entries.begin(),entries.end());
    messages.resize(capacity,0); writes.push_back({messageBase,std::move(messages)});
    for (const auto* name:{"ptrCustomMessageEntries","numCustomMessageEntries"}) {
        const auto [address,size]=range(name);Require(size==4,"Invalid message pointer ABI");
        std::vector<std::uint8_t> value(4);
        Write32(value,0,std::string_view(name)=="ptrCustomMessageEntries" ? messageBase+entryOffset : entries.size()/0x60);
        writes.push_back({address,std::move(value)});
    }
    // Only these known data tables may be changed outside the payload.
    const std::map<std::uint32_t,std::size_t> allowed{{0x52236c,22},{0x54c222,108},{0x54c8b0,14}};
    for (const auto& patch:seed.value("native_patches",Json::array())) {
        auto address=patch.at("address").get<std::uint32_t>();
        Require(allowed.contains(address),"Seed requests a code or unknown data patch");
        auto bytes=Decode(patch.at("data_hex"),allowed.at(address));
        Require(bytes.size()==allowed.at(address),"Invalid native table size");
        writes.push_back({address,std::move(bytes)});
    }
    std::sort(writes.begin(),writes.end(),[](const auto& a,const auto& b){return a.address<b.address;});
    for (std::size_t i=1;i<writes.size();++i)
        Require(std::uint64_t(writes[i-1].address)+writes[i-1].bytes.size()<=writes[i].address,
                "Overlapping seed destinations");
    return writes;
}
}
