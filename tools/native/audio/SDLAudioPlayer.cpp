#include "ship/audio/SDLAudioPlayer.h"
#include <spdlog/spdlog.h>
#include <cstring>
#include "ship/audio/retuned_output_gain.h"

namespace Ship {
SDLAudioPlayer::~SDLAudioPlayer() {
    DoClose();
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}
void SDLAudioPlayer::DoClose() {
    if (mDevice) {
        SDL_PauseAudioDevice(mDevice, 1);
        SDL_CloseAudioDevice(mDevice);
        mDevice = 0;
    }
}
bool SDLAudioPlayer::DoInit() {
    if (SDL_Init(SDL_INIT_AUDIO) != 0) return false;
    mNumChannels = GetNumOutputChannels();
    mPcm.Configure(GetSampleRate(), mNumChannels, std::max(1, GetDesiredBuffered()));
    SDL_AudioSpec want{}, have{};
    want.freq = GetSampleRate();
    want.format = AUDIO_S16SYS;
    want.channels = mNumChannels;
    want.samples = 512;
    want.userdata = this;
    want.callback = [](void* userdata, Uint8* bytes, int length) {
        auto& player = *static_cast<SDLAudioPlayer*>(userdata);
        std::memset(bytes, 0, length);
        auto output=std::span<int16_t>{reinterpret_cast<int16_t*>(bytes), size_t(length) / sizeof(int16_t)};
        player.mPcm.Render(output);
        Retuned::ApplyOutputGain(output,Retuned::OutputVolume.load(),Retuned::OutputMuted.load());
    };
    mDevice = SDL_OpenAudioDevice(nullptr, 0, &want, &have, 0);
    if (!mDevice) {
        SPDLOG_ERROR("SDL_OpenAudio error: {}", SDL_GetError());
        return false;
    }
    SPDLOG_INFO("SDL Audio: {} channels, {} Hz, {} callback frames, {} prebuffer frames",
                mNumChannels, want.freq, have.samples, GetDesiredBuffered());
    SDL_PauseAudioDevice(mDevice, 0);
    return true;
}
int SDLAudioPlayer::Buffered() {
    if (!mDevice) return 0;
    SDL_LockAudioDevice(mDevice);
    const auto count = mPcm.Buffered();
    SDL_UnlockAudioDevice(mDevice);
    return static_cast<int>(count);
}
uint64_t SDLAudioPlayer::OutputUnderruns() const {
    if (!mDevice) return 0;
    SDL_LockAudioDevice(mDevice);
    const auto count = mPcm.Underruns();
    SDL_UnlockAudioDevice(mDevice);
    return count;
}
void SDLAudioPlayer::DoPlay(const uint8_t* bytes, size_t length) {
    if (!mDevice) return;
    SDL_LockAudioDevice(mDevice);
    mPcm.Push({reinterpret_cast<const int16_t*>(bytes), length / sizeof(int16_t)});
    SDL_UnlockAudioDevice(mDevice);
}
void SDLAudioPlayer::DoFlush() {
    if (!mDevice) return;
    SDL_LockAudioDevice(mDevice);
    mPcm.Flush();
    SDL_UnlockAudioDevice(mDevice);
}
}
