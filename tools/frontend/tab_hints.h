#pragma once
#include <imgui.h>
#include <atomic>
#include <chrono>
#include <algorithm>
namespace RetunedFrontend {
inline std::atomic<int64_t> TabHintsUntil{0};
inline int64_t HintTime(){return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
inline void PublishTabHints(){TabHintsUntil.store(HintTime()+100);}
inline void DrawTabHints(){
    if(HintTime()>TabHintsUntil.load())return;
    const auto* view=ImGui::GetMainViewport();auto* d=ImGui::GetForegroundDrawList();
    const float f=std::clamp(view->WorkSize.y*.026f,16.f,24.f),h=f*1.5f,w=f*2;
    const float x=view->WorkPos.x+view->WorkSize.x*.80f-f*5,y=view->WorkPos.y+view->WorkSize.y*.92f-h*.5f;
    const auto color=IM_COL32(240,243,250,255),bg=IM_COL32(22,30,44,235),edge=IM_COL32(155,177,206,255);
    auto shoulder=[&](float left,const char* label){d->AddRectFilled({left,y},{left+w,y+h},bg,f*.3f);d->AddRect({left,y},{left+w,y+h},edge,f*.3f,0,1.5f);d->AddText(ImGui::GetFont(),f,{left+f*.65f,y+f*.25f},color,label);};
    shoulder(x,"L");shoulder(x+f*8,"R");
    d->AddTriangleFilled({x+f*2.7f,y+h*.5f},{x+f*3.2f,y+h*.2f},{x+f*3.2f,y+h*.8f},color);
    d->AddText(ImGui::GetFont(),f,{x+f*3.8f,y+f*.25f},color,"Tabs");
    d->AddTriangleFilled({x+f*7.3f,y+h*.5f},{x+f*6.8f,y+h*.2f},{x+f*6.8f,y+h*.8f},color);
}
}
