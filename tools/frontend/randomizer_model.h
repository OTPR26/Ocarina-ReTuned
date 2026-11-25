// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <functional>
#include <string>

namespace RetunedFrontend {
enum class RandomizerSlotStatus { Empty, Ready, Unavailable };
struct RandomizerSlotView {
    RandomizerSlotStatus Status = RandomizerSlotStatus::Empty;
    std::string Seed;
    std::string Message;
};
struct RandomizerMenuState {
    // Installed only by a host with a validated seed launcher and save isolation.
    std::function<void()> Refresh;
    std::function<void()> StartNormal;
    std::function<void(unsigned, const std::string&)> Create;
    std::function<void(unsigned)> Start;
    // Document adapters supply bytes, never a URI that the runtime must reopen.
    std::function<void(unsigned, const std::string&)> Import;
    std::function<std::string(unsigned)> Export;
    std::function<void(unsigned)> ChooseImport, ChooseExport;
    std::function<void()> DrawTransfer;
    std::array<RandomizerSlotView, 3> Slots{};
    std::array<char, 129> SeedInput{};
    bool Busy = false;
    bool TransferBusy = false;
    std::string TransferStatus;
    bool SlotsVisible = false;
    bool FocusSlots = false;
    bool SelectedAtStartup = false;
    int ActiveSlot = -1;
    std::string ActiveSeed;
    std::string Status;
    bool Available() const { return Refresh && Create && Start; }
    bool CanCreate(unsigned slot, bool startup) const {
        return Available() && startup && !Busy && !TransferBusy && slot < Slots.size() &&
               Slots[slot].Status == RandomizerSlotStatus::Empty;
    }
    bool CanStart(unsigned slot, bool startup) const {
        return Available() && startup && !Busy && !TransferBusy && slot < Slots.size() &&
               Slots[slot].Status == RandomizerSlotStatus::Ready;
    }
};
inline RandomizerMenuState RandomizerMenu;
}
