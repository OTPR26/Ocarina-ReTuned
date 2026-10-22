// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "ship/Context.h"
#include "ship/controller/controldeck/ControlDeck.h"
#include <backends/imgui_impl_sdl2.h>
#include <vector>
namespace RetunedFrontend {
// Borrow the gameplay device manager's live handles. ImGui's independent auto
// discovery can miss controllers during startup or after reconnecting.
inline void UpdateMenuGamepads() {
 auto* context=Ship::Context::GetRawInstance();
 auto deck=context?context->GetControlDeck():nullptr;
 auto devices=deck?deck->GetConnectedPhysicalDeviceManager():nullptr;
 if(!devices)return;
 devices->RefreshConnectedSDLGamepads();
 std::vector<SDL_GameController*> pads;
 for(const auto& [id,pad]:devices->GetConnectedSDLGamepadsForPort(0))
  if(pad && SDL_GameControllerGetAttached(pad))pads.push_back(pad);
 // Manual mode copies the list and does not close the borrowed handles.
 ImGui_ImplSDL2_SetGamepadMode(ImGui_ImplSDL2_GamepadMode_Manual,
                             pads.empty()?nullptr:pads.data(),static_cast<int>(pads.size()));
}
}
