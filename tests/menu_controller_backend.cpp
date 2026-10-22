// SPDX-License-Identifier: GPL-2.0-or-later
#include <SDL.h>
#include <imgui.h>
#include <backends/imgui_impl_sdl2.h>
#include <cassert>
#include <cstdio>
int main() {
 SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
 assert(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER)==0);
 auto* window=SDL_CreateWindow("menu input regression",0,0,640,480,SDL_WINDOW_HIDDEN);
 assert(window);ImGui::CreateContext();auto& io=ImGui::GetIO();
 io.IniFilename=nullptr;io.LogFilename=nullptr;
 io.ConfigFlags|=ImGuiConfigFlags_NavEnableGamepad|ImGuiConfigFlags_NavEnableKeyboard;
 assert(ImGui_ImplSDL2_InitForOther(window));
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,6,21,0);assert(device>=0);
 auto* pad=SDL_GameControllerOpen(device);assert(pad);
 auto* joystick=SDL_GameControllerGetJoystick(pad);
 // Deliberately disable independent discovery. Only the borrowed gameplay handle
 // can deliver input to the frontend, before any guest game frame is executed.
 ImGui_ImplSDL2_SetGamepadMode(ImGui_ImplSDL2_GamepadMode_Manual,&pad,1);
 unsigned char* pixels;int w,h;io.Fonts->GetTexDataAsRGBA32(&pixels,&w,&h);
 bool settings=false;
 auto frame=[&] {
  SDL_PumpEvents();SDL_JoystickUpdate();ImGui_ImplSDL2_NewFrame();io.DisplaySize={640,480};io.DeltaTime=1.f/60;
  ImGui::NewFrame();ImGui::SetNextWindowSize({600,400});ImGui::Begin("Startup");
  ImGui::Button("Start game");if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
  if(ImGui::Button("Settings"))settings=true;
  ImGui::End();ImGui::Render();
 };
 auto press=[&](SDL_GameControllerButton b) {
  assert(SDL_JoystickSetVirtualButton(joystick,b,1)==0);frame();frame();
  assert(SDL_JoystickSetVirtualButton(joystick,b,0)==0);frame();frame();
 };
 frame();frame();press(SDL_CONTROLLER_BUTTON_DPAD_DOWN);press(SDL_CONTROLLER_BUTTON_A);
 assert(settings);
 // Removing ImGui's list must not close the gameplay device's borrowed handle.
 ImGui_ImplSDL2_SetGamepadMode(ImGui_ImplSDL2_GamepadMode_Manual,nullptr,0);frame();
 assert(SDL_GameControllerGetAttached(pad));
 assert(!(io.BackendFlags&ImGuiBackendFlags_HasGamepad));
 ImGui_ImplSDL2_SetGamepadMode(ImGui_ImplSDL2_GamepadMode_Manual,&pad,1);frame();
 assert(io.BackendFlags&ImGuiBackendFlags_HasGamepad);
 ImGui_ImplSDL2_Shutdown();ImGui::DestroyContext();SDL_GameControllerClose(pad);
 SDL_JoystickDetachVirtual(device);SDL_DestroyWindow(window);SDL_Quit();
 std::puts("Startup D-pad/A, borrowed ownership and reconnect checks PASS");
}
