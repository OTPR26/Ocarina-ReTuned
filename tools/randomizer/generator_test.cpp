#include "generator.h"
#include <stdexcept>
#include <iostream>
#include <nlohmann/json.hpp>
int main() {
    const auto a=RetunedRandomizer::Generate("retuned-proof-001");
    const auto parsed=nlohmann::json::parse(a);
    if(parsed.at("runtime_ready")!=false || parsed.at("items").size()!=337)
        throw std::runtime_error("Unexpected proof seed shape");
    const auto b=RetunedRandomizer::Generate("retuned-proof-002");
    const auto again=RetunedRandomizer::Generate("retuned-proof-001");
    if(a!=again || a==b)throw std::runtime_error("Seed determinism/isolation failed");
    bool cancelled=false;
    try {RetunedRandomizer::Generate("cancelled",[](unsigned){throw std::runtime_error("cancelled");});}
    catch(const std::runtime_error&){cancelled=true;}
    if(!cancelled || RetunedRandomizer::Generate("retuned-proof-001")!=a)
        throw std::runtime_error("Cancellation recovery failed");
    bool rejected=false;try {RetunedRandomizer::Generate("");}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("Empty seed accepted");
    std::cerr<<"Repeated generation, independent seeds, cancellation recovery, and invalid input passed.\n";
}
