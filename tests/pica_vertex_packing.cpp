#include "fast/oot3d/pica_nri_vertex_input.h"
#include <array>
#include <cassert>
#include <cstring>
using namespace Fast::Oot3d;
int main() {
    // Three-byte source formats need not be GPU vertex formats: the NRI path
    // must preserve their numeric values in a four-float attribute instead.
    for (auto scalar : {PicaNriVertexScalar::SignedByte, PicaNriVertexScalar::UnsignedByte}) {
        std::array<PicaNriSourceVertexBinding,1> bindings{{{0,3,false}}};
        std::array<PicaNriSourceVertexAttribute,1> attributes{{{0,0,scalar,3,0}}};
        auto layout=BuildPicaNriVertexInputLayout(bindings,attributes);
        assert(layout.Valid() && layout.Bindings[0].ByteStride==16);
        std::array<uint8_t,6> source{0x80,0xff,0x7f,0,1,2};
        std::vector<uint8_t> packed;
        assert(RepackPicaNriVertexBinding(bindings[0],layout.Attributes,16,source,packed));
        assert(packed.size()==32);
        std::array<float,8> values{}; std::memcpy(values.data(),packed.data(),32);
        assert(values[0]==(scalar==PicaNriVertexScalar::SignedByte ? -128.f : 128.f));
        assert(values[1]==(scalar==PicaNriVertexScalar::SignedByte ? -1.f : 255.f));
        assert(values[2]==127 && values[3]==1 && values[4]==0 && values[5]==1 && values[6]==2 && values[7]==1);
        assert(!RepackPicaNriVertexBinding(bindings[0],layout.Attributes,16,std::span(source).first(5),packed));
    }
}
