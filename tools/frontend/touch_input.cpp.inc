  if(RetunedFrontend::NativeFrontendEnabled) {
    const bool chord=selectedController.Controller &&
      SDL_GameControllerGetButton(selectedController.Controller,SDL_CONTROLLER_BUTTON_LEFTSTICK) &&
      SDL_GameControllerGetButton(selectedController.Controller,SDL_CONTROLLER_BUTTON_RIGHTSTICK);
    host.Actions[static_cast<size_t>(NativeControlAction::Start)] |= chord;
    const auto touch=RetunedFrontend::SampleTouch(guestRefreshWillConsume);
    if(!hostGuiVisible) {
      using T=RetunedFrontend::TouchAction;
      for(const auto [touchAction,gameAction]:std::initializer_list<std::pair<T,NativeControlAction>>{
        {T::A,NativeControlAction::A},{T::B,NativeControlAction::B},
        {T::X,NativeControlAction::X},{T::Y,NativeControlAction::Y},
        {T::Target,NativeControlAction::L},{T::Shield,NativeControlAction::R},
        {T::Map,NativeControlAction::Zl},{T::ItemI,NativeControlAction::Zl},{T::ItemII,NativeControlAction::Zr},
        {T::Inventory,NativeControlAction::Select},{T::Settings,NativeControlAction::Start},
        {T::Up,NativeControlAction::DpadUp},{T::Down,NativeControlAction::DpadDown},
        {T::Left,NativeControlAction::DpadLeft},{T::Right,NativeControlAction::DpadRight}})
          host.Actions[static_cast<size_t>(gameAction)] |= (touch.Buttons&RetunedFrontend::TouchModel::Bit(touchAction))!=0;
      if(touch.MoveX||touch.MoveY){host.LeftStickX=static_cast<int16_t>(touch.MoveX*32767);host.LeftStickY=static_cast<int16_t>(touch.MoveY*32767);}
      if(touch.LookX||touch.LookY){host.RightStickX=static_cast<int16_t>(touch.LookX*32767);host.RightStickY=static_cast<int16_t>(touch.LookY*32767);}
    }
  }
