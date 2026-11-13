#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void RetunedTouchSetHudAnchor(int slot,float x,float y);
void RetunedTouchSetHudScale(int slot,float scale);
void RetunedTouchSetHudDisplay(float width,float height);
void RetunedTouchSetButton(int button,int pressed);
void RetunedTouchSetEnabled(int enabled);
void RetunedTouchSetAxis(int axis,int value);
#ifdef __cplusplus
}
#endif
