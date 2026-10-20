#include "../tools/native/audio/output_gain.h"
#include <array>
#include <cassert>
#include <limits>
int main(){
 const std::array<int16_t,5> input{-32768,-10000,0,10000,32767};
 auto output=input;Retuned::ApplyOutputGain(output,1.f,false);assert(output==input);
 Retuned::ApplyOutputGain(output,.5f,false);assert((output==std::array<int16_t,5>{-16384,-5000,0,5000,16383}));
 output=input;Retuned::ApplyOutputGain(output,1.f,true);for(auto sample:output)assert(sample==0);
 output=input;Retuned::ApplyOutputGain(output,-1.f,false);for(auto sample:output)assert(sample==0);
 output=input;Retuned::ApplyOutputGain(output,10.f,false);assert(output==input);
 output=input;Retuned::ApplyOutputGain(output,std::numeric_limits<float>::quiet_NaN(),false);assert(output==input);
}
