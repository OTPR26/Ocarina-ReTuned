#pragma once
#include <optional>
#include <string>
#include <vector>

namespace RetunedSetup {
struct GameLaunch {
    std::vector<std::string> arguments;
    int randomizerSlot = -1;
    bool newGame = false;
};
class GameHandoff {
public:
    bool Queue(GameLaunch launch) {
        if (pending_ || launch.arguments.empty() || launch.randomizerSlot < -1 ||
            launch.randomizerSlot > 2 || (launch.randomizerSlot < 0 && launch.newGame)) return false;
        for (const auto& argument : launch.arguments)
            if (argument.empty() || argument.find('\0') != std::string::npos) return false;
        pending_ = std::move(launch);
        return true;
    }
    bool Pending() const { return pending_.has_value(); }
    void Cancel() { pending_.reset(); }
    // Consume only after the current guest and renderer have been destroyed.
    std::optional<GameLaunch> Take() {
        auto result = std::move(pending_);
        pending_.reset();
        return result;
    }
private:
    std::optional<GameLaunch> pending_;
};
}
