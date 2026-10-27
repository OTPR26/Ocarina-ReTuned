#include "../tools/native/setup/preparation_version.h"
#include <cassert>
int main(int argc,char** argv) {
 assert(argc==2);
 const auto root=std::filesystem::path(argv[1]);
 const auto profile=root/"native-launch.json",receipt=root/"setup-receipt.json";
 const std::string identity(64,'a');
 using RetunedSetup::PreparedIdentityMatches;
 assert(!PreparedIdentityMatches(profile,identity));
 std::ofstream(profile)<<nlohmann::json{{"arguments",{"--a32-process-manifest",(root/"process-manifest.json").string()}}};
 assert(!PreparedIdentityMatches(profile,identity));
 std::ofstream(receipt)<<nlohmann::json{{"preparation_identity",std::string(64,'b')}};
 assert(!PreparedIdentityMatches(profile,identity));
 std::ofstream(receipt)<<nlohmann::json{{"preparation_identity",identity}};
 assert(PreparedIdentityMatches(profile,identity));
 assert(!PreparedIdentityMatches(profile,"invalid"));
 std::ofstream(receipt)<<"damaged JSON";
 assert(!PreparedIdentityMatches(profile,identity));
 std::ofstream(profile)<<nlohmann::json{{"arguments",{"--a32-process-manifest"}}};
 assert(!PreparedIdentityMatches(profile,identity));
}
