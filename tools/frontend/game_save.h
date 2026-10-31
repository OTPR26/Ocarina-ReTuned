// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
namespace RetunedFrontend {
class GameSaveShortcut {
 public:
    void SetAvailable(bool available) {
        mAvailable = available;
        if (!available) { mRequested = false; mVisible = false; }
    }
    bool Available() const { return mAvailable.load(); }
    bool Pending() const { return mRequested.load(); }
    bool Visible() const { return mVisible.load(); }
    bool DialogOpen() const { return mDialog.load(); }
    bool Dual() const { return mDual.load(); }
    void SetDialog(bool open) {mDialog=open;if(!open)mBackRequested=false;}
    void RequestBack() {if(DialogOpen())mBackRequested=true;}
    bool ConsumeDialogTouch(int x,int y,bool pressed) {
        if(!DialogOpen()||!pressed||y<202)return false;
        if(x>=0&&x<58)RequestBack();
        return true;
    }
    bool BackInput(bool guestRefresh) {
        if(!DialogOpen()){mBackFrames=0;return false;}
        if(!guestRefresh)return false;
        if(mBackRequested.exchange(false))mBackFrames=6;
        if(!mBackFrames)return false;
        --mBackFrames;return true;
    }
    bool Request() {
        if (!Available()) return false;
        mRequested = true;
        return true;
    }
    bool Take(bool dual, bool playing, bool hostMenu) {
        mDual=dual;
        mVisible = dual && playing && !hostMenu && Available();
        if (!dual || !playing || !Available()) {
            mRequested = false;
            return false;
        }
        if (hostMenu) return false;
        return mRequested.exchange(false);
    }
 private:
    std::atomic<bool> mAvailable{false}, mRequested{false}, mVisible{false};
    std::atomic<bool> mDialog{false},mBackRequested{false},mDual{false};
    unsigned mBackFrames=0;
};
inline GameSaveShortcut GameSave;
}
