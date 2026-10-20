#include "oot3d_native_control_config.h"
#include <cassert>
#include <filesystem>
#include <string>
#include <memory>
#include <utility>
#include <unistd.h>
using namespace Oot3dNativeGame;
// Exercise the same completed-edit path included by the Controls panel.
struct TopSettings {
  struct State { int Config=0; };
  State Snapshot() { return {}; }
  bool Apply(int, std::string*) { return true; }
};
struct Editor {
  std::shared_ptr<NativeControlConfigRuntime> mControls;
  std::shared_ptr<TopSettings> mTopScreen;
  NativeControlConfig mControlDraft, mSavedControls;
  std::uint64_t mObservedControlRevision=0;
  bool mControlDirty=true, mCameraDirty=false;
  int mTopDraft=0, mSavedTop=0;
  std::string mStatus;
  void CompleteEdit(const NativeControlConfig& frameStartDraft) {
    const int frameStartTopDraft=mTopDraft;
#include "../tools/frontend/control_changes.cpp.inc"
  }
};
int main() {
  const auto dir=std::filesystem::temp_directory_path()/ ("retuned-controls-"+std::to_string(getpid()));
  std::filesystem::create_directories(dir);
  const auto path=dir/"controls.json";
  const auto defaults=NativeControlPreset(NativeControlProfile::Controller);
  NativeControlConfigRuntime runtime(path, defaults);
  auto custom=defaults;
  custom.Profile=NativeControlProfile::Custom;
  std::swap(custom.Bindings[static_cast<size_t>(NativeControlAction::A)],
            custom.Bindings[static_cast<size_t>(NativeControlAction::B)]);
  custom.Bindings[static_cast<size_t>(NativeControlAction::L)].Gamepad=NativeGamepadButton::RightShoulder;
  custom.LookStickDeadZonePercent=23;
  std::string error;
  Editor editor;
  editor.mControls=std::make_shared<NativeControlConfigRuntime>(path,defaults);
  editor.mControlDraft=custom;
  editor.CompleteEdit(defaults);
  assert(!editor.mControlDirty && editor.mStatus=="Saved");
  assert(editor.mControls->Snapshot().Config==custom);
  assert(runtime.Reload(&error));
  NativeControlConfigRuntime reopened(path, defaults);
  assert(reopened.Reload(&error));
  assert(reopened.Snapshot().Config==custom);
  // A failed replacement must leave both the live and saved mappings intact.
  std::filesystem::create_directory(path.string()+".tmp");
  editor.mControlDraft=defaults;
  editor.CompleteEdit(custom);
  assert(editor.mControlDirty && editor.mStatus!="Saved");
  assert(editor.mControls->Snapshot().Config==custom);
  assert(runtime.Snapshot().Config==custom);
  assert(reopened.Reload(&error) && reopened.Snapshot().Config==custom);
  std::filesystem::remove_all(dir);
}
