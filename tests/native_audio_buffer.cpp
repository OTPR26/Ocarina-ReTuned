#include "../tools/native/audio/pcm_buffer.h"
#include <cassert>
#include <cmath>
#include <vector>
int main() {
    Retuned::PcmBuffer queue;
    queue.Configure(32000,2,3200);
    std::vector<int16_t> packet(160*2,12000), output(160*2);
    for(int i=0;i<19;++i) { queue.Push(packet); queue.Render(output); for(auto s:output)assert(s==0); }
    assert(queue.Underruns()==0 && queue.Buffered()==3040);
    queue.Push(packet);queue.Render(output);
    assert(output.front()==0 && output.back()>11000 && queue.Buffered()==3040);
    for(int i=0;i<200;++i){queue.Push(packet);queue.Render(output);assert(queue.Buffered()==3040);}
    int16_t last=output.back();
    for(int i=0;i<25;++i) {
        queue.Render(output);
        for(size_t j=0;j<output.size();j+=2){assert(std::abs(int(output[j])-last)<=100);last=output[j];}
    }
    assert(queue.Underruns()==1 && queue.Buffered()==0 && last==0);
    for(int i=0;i<20;++i) queue.Push(packet);
    queue.Render(output);assert(output.front()==0 && output.back()>11000);
    queue.Flush();assert(queue.Buffered()==0);
    queue.Render(output);for(auto s:output)assert(s==0);
    // Ring wrap, irregular delivery and callback sizes must preserve channel order.
    queue.Configure(32000,2,1600);
    std::vector<int16_t> coded(160*2);
    for(size_t i=0;i<coded.size();i+=2){coded[i]=1234;coded[i+1]=-2345;}
    for(int i=0;i<10;++i)queue.Push(coded);
    std::vector<int16_t> shortOutput(80*2);
    for(int i=0;i<2000;++i){
        if(i%2==0)queue.Push(coded);
        queue.Render(shortOutput);
        if(i>3)for(size_t j=0;j<shortOutput.size();j+=2)assert(shortOutput[j]==1234 && shortOutput[j+1]==-2345);
    }
    assert(queue.Underruns()==0);
    std::vector<int16_t> overflow(40000,42);queue.Push(overflow);
    assert(queue.Buffered()<=8000);
    queue.Render(output);assert(output.front()==0);
    queue.Configure(32000,6,3200);std::vector<int16_t> surround(3200*6,16000);
    queue.Push(surround);queue.Render(surround);assert(queue.Buffered()==0);
    queue.Render(surround);assert(queue.Underruns()==1);
}
