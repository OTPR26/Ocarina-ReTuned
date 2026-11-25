
static int RunSwitchSessions(int argc, char** argv) {
    std::vector<std::string> args;
    std::vector<char*> pointers;
    for (;;) {
        const int status = RunSwitchGuest(argc, argv);
        auto next = RetunedRandomizer::SwitchHandoff.Take();
        if (status || !next) return status;
        auto& menu = RetunedFrontend::RandomizerMenu;
        menu.ActiveSlot = next->randomizerSlot;
        menu.ActiveSeed.clear();
        unsetenv("RETUNED_RANDOMIZER_ACTIVE_SLOT");
        unsetenv("RETUNED_RANDOMIZER_NEW_GAME");
        unsetenv("RETUNED_RANDOMIZER_START_NORMAL");
        if (next->randomizerSlot < 0) setenv("RETUNED_RANDOMIZER_START_NORMAL", "1", 1);
        if (next->randomizerSlot >= 0) {
            const auto flag = std::find(next->arguments.begin(), next->arguments.end(), "--title-plugin");
            if (flag == next->arguments.end() || flag+1 == next->arguments.end() ||
                std::filesystem::path(*(flag+1)) != RetunedRandomizer::SwitchData / "runtime/title.id")
                throw std::runtime_error("Invalid static Randomizer title selection");
            next->arguments.erase(flag, flag+2);
            SDL_setenv("RETUNED_RANDOMIZER_ACTIVE_SLOT", std::to_string(next->randomizerSlot).c_str(), 1);
            if (next->newGame) SDL_setenv("RETUNED_RANDOMIZER_NEW_GAME", "1", 1);
            menu.ActiveSeed = RetunedRandomizer::RunCatalog(RetunedRandomizer::SwitchData).Read(next->randomizerSlot).seed;
        }
        RetunedFrontend::StartupVisible = false;
        RetunedFrontend::SetupVisible = false;
        args = std::move(next->arguments);
        args.insert(args.begin(), "Ocarina ReTuned");
        pointers.clear();
        for (auto& arg : args) pointers.push_back(arg.data());
        argc = static_cast<int>(pointers.size());
        argv = pointers.data();
    }
}

int main(int argc, char** argv) {
    try { return RunSwitchSessions(argc, argv); }
    catch (const std::exception& e) {
        std::fprintf(stderr, "Could not start Switch session: %s\n", e.what());
        return 1;
    }
}
