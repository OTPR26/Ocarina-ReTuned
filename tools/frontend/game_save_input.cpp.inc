  // Deliver the native Save input after the Settings shortcut is consumed.
  // The existing Start latch retains a tap until the next guest refresh.
  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed &&
      RetunedFrontend::GameSave.Take(RetunedFrontend::ProbeGuestDualActive.load(),
          !RetunedFrontend::StartupVisible && !RetunedFrontend::SetupVisible, hostGuiVisible)) {
    physicalInputFrame.Hid.Buttons |= Oot3dNativeGame::NativeA32HidButtonMask(
        Oot3dNativeGame::NativeA32HidButton::Start);
  }
  if (RetunedFrontend::GameSave.ConsumeDialogTouch(physicalInputFrame.Hid.TouchX,
          physicalInputFrame.Hid.TouchY,physicalInputFrame.Hid.TouchPressed))
    physicalInputFrame.Hid.TouchPressed=false;
  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed &&
      RetunedFrontend::GameSave.BackInput(guestRefreshesDue != 0U)) {
    physicalInputFrame.Hid.Buttons |= Oot3dNativeGame::NativeA32HidButtonMask(
        Oot3dNativeGame::NativeA32HidButton::B);
  }
