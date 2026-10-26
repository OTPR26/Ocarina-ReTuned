#include "duo_game_display.h"
#include <cassert>
using namespace RetunedFrontend;
int main() {
    DuoGameDisplay display;
    assert(display.Requested(true)==GamePresentation::Single);
    assert(!display.Layout(100,200,true).Top.Width);
    display.Publish({true,false,{10,20,900,700},{20,40,880,660},{440,20,40,700},{}});
    assert(display.Requested(true)==GamePresentation::Single);
    display.Select(ScreenPreference::Dual);
    assert(display.Requested(true)==GamePresentation::Dual);
    assert(display.Requested(false)==GamePresentation::Single);
    auto layout=display.Layout(900,700,true), retina=display.Layout(2700,2100,true);
    assert(layout.Top.X+layout.Top.Width<=430 && layout.Lower.X>=470);
    assert(retina.Lower.X==3*layout.Lower.X);
    const float x=layout.Lower.X+layout.Lower.Width/2,y=layout.Lower.Y+layout.Lower.Height/2;
    auto touch=display.Touch(900,700,true,x,y), scaled=display.Touch(2700,2100,true,3*x,3*y);
    assert(touch && touch->X==160 && touch->Y==120);
    assert(scaled && scaled->X==160 && scaled->Y==120);
    assert(!display.Touch(900,700,false,x,y));
    assert(!display.Touch(900,700,true,450,y));
    display.Publish({true,false,{10,20,900,700},{20,40,880,660},{440,20,40,700},{{x+5,y+15,10,10}}});
    assert(!display.Touch(900,700,true,x,y));
    display.Publish({true,true,{0,0,400,700},{0,20,400,660},{},{}});
    assert(display.Requested(true)==GamePresentation::Single);
    assert(!display.Layout(400,700,true).Lower.Width);
    display.Publish({true,false,{0,0,700,900},{0,20,700,860},{0,420,700,40},{}});
    assert(display.Requested(true)==GamePresentation::Dual);
    assert(display.Layout(700,900,true).Lower.Y>=460);
    LowerEquipmentPanelEnabled=false;
    const auto centered=display.Layout(700,900,true);
    LowerEquipmentPanelEnabled=true;
    const auto aligned=display.Layout(700,900,true);
    const auto pane=display.LowerPanelBounds(700,900,true);
    assert(aligned.Lower.Y==pane.Y && centered.Lower.Y>=aligned.Lower.Y);
    assert(aligned.Lower.Width==centered.Lower.Width && aligned.Lower.Height==centered.Lower.Height);
    auto alignedTouch=display.Touch(700,900,true,aligned.Lower.X+aligned.Lower.Width/2,aligned.Lower.Y+aligned.Lower.Height/2);
    assert(alignedTouch && alignedTouch->X==160 && alignedTouch->Y==120);
    assert(!display.Touch(700,900,true,aligned.Lower.X+1,aligned.Lower.Y+aligned.Lower.Height+1));
    display.Select(ScreenPreference::Hybrid); // not exposed/accepted yet
    assert(display.Requested(true)==GamePresentation::Dual);
    display.Select(ScreenPreference::Single);
    assert(display.Requested(true)==GamePresentation::Single);
}
