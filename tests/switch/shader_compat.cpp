// SPDX-License-Identifier: GPL-2.0-or-later
#include "shader_compat.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char** argv){
 assert(argc==3);
 std::ifstream in(argv[1]);assert(in);
 std::string text((std::istreambuf_iterator<char>(in)),{});
 RetunedSwitchShader::Rewrite(text);
 const auto once=text;RetunedSwitchShader::Rewrite(text);assert(text==once);
 std::ofstream out(argv[2]);out<<text;assert(out);
 std::string unrelated="#version 430\nvoid main(){}";const auto before=unrelated;
 RetunedSwitchShader::Rewrite(unrelated);assert(unrelated==before);
 bool rejected=false;try{std::string changed="int pt_rand1(int v) {";RetunedSwitchShader::Rewrite(changed);}catch(const std::runtime_error&){rejected=true;}
 assert(rejected);
 std::cout<<"PASS: rewrite is stable, leaves unrelated shaders intact, and rejects changed contexts\n";
}
