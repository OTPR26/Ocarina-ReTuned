#pragma once
namespace RetunedFrontend {
class OcarinaShortcutLifecycle {
  public:
    bool Finished(bool open,bool ready) {
        if(!open){mReadySeen=false;return false;}
        if(ready){mReadySeen=true;return false;}
        if(!mReadySeen)return false;
        mReadySeen=false;return true;
    }
  private:bool mReadySeen=false;
};
}
