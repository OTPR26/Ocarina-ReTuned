#pragma once

#ifdef __cplusplus
extern "C" {
#endif

int RetunedIOS_TouchControlsAvailable(void);
void RetunedIOS_SetTouchControlsEnabled(int enabled);
void RetunedIOS_SetTouchOpacity(float opacity);
void RetunedIOS_SetTouchScale(float scale);
void RetunedIOS_SetExtraShoulders(int enabled);
void RetunedIOS_SetTouchHudIcons(int enabled);
void RetunedIOS_SetFaceButtonLayout(int layout);
void RetunedIOS_SetTouchLeftStickFloating(int floating);
void RetunedIOS_SetTouchControlsMenuVisible(int visible);

void RetunedIOS_SetManualJump(int mode);

#ifdef __cplusplus
}
#endif
