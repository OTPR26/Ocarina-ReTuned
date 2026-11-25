#pragma once
#include "../native/setup/game_handoff.h"
#include <mutex>

namespace RetunedRandomizer {
// The frontend queues a request; only the session owner consumes it after
// draining rendering and destroying the previous guest.
class AndroidSessionQueue {
public:
    bool Queue(std::vector<std::string> arguments,int slot,bool fresh) {
        std::lock_guard lock(mutex_);
        if(!handoff_.Queue({std::move(arguments),slot,fresh}))return false;
        pending_=true;return true;
    }
    bool Pending() const {std::lock_guard lock(mutex_);return pending_;}
    std::optional<RetunedSetup::GameLaunch> Take() {
        std::lock_guard lock(mutex_);pending_=false;return handoff_.Take();
    }
private:
    mutable std::mutex mutex_;
    RetunedSetup::GameHandoff handoff_;
    bool pending_=false;
};
inline AndroidSessionQueue AndroidSessions;
}
