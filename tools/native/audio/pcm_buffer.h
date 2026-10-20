#pragma once
#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace Retuned {
// Callers serialize producer/device access. The callback neither allocates nor waits.
class PcmBuffer {
  public:
    void Configure(uint32_t rate, uint32_t channels, uint32_t targetFrames) {
        mChannels = channels;
        mTarget = std::max(1U, targetFrames);
        mFadeFrames = std::max(1U, rate / 200U);
        mCapacity = std::max(rate / 4U, mTarget * 3U);
        mData.assign(size_t{mCapacity} * channels, 0);
        mLast.assign(channels, 0);
        mTail.assign(channels, 0);
        mUnderruns = 0;
        Flush();
    }
    void Flush() {
        mRead = mCount = mFadeIn = 0;
        mFadeOut = mFadeFrames;
        mPriming = true;
        std::fill(mLast.begin(), mLast.end(), 0);
        std::fill(mTail.begin(), mTail.end(), 0);
    }
    uint32_t Buffered() const { return mCount; }
    uint64_t Underruns() const { return mUnderruns; }
    void Push(std::span<const int16_t> input) {
        if (!mChannels) return;
        size_t frames = input.size() / mChannels;
        if (frames > mCapacity) {
            input = input.last(size_t{mCapacity} * mChannels);
            frames = mCapacity;
        }
        if (frames + mCount > mCapacity) {
            const uint32_t drop = static_cast<uint32_t>(frames + mCount - mCapacity);
            mRead = (mRead + drop) % mCapacity;
            mCount -= drop;
            mPriming = true;
            mFadeIn = 0;
        }
        for (size_t i = 0; i < frames; ++i) {
            const size_t frame = (mRead + mCount) % mCapacity;
            std::copy_n(input.data() + i*mChannels, mChannels, mData.data() + frame*mChannels);
            ++mCount;
        }
    }
    void Render(std::span<int16_t> output) {
        std::fill(output.begin(), output.end(), 0);
        if (!mChannels) return;
        for (size_t i = 0; i < output.size() / mChannels; ++i) {
            if (mPriming && mCount >= mTarget) { mPriming = false; mFadeIn = 0; }
            if (!mPriming && mCount == 0) {
                mPriming = true;
                mTail = mLast;
                mFadeOut = 0;
                ++mUnderruns;
            }
            for (uint32_t channel = 0; channel < mChannels; ++channel) {
                int32_t sample = 0;
                if (!mPriming) {
                    sample = mData[size_t{mRead} * mChannels + channel];
                    if (mFadeIn < mFadeFrames) sample = sample * static_cast<int32_t>(mFadeIn) / static_cast<int32_t>(mFadeFrames);
                } else if (mFadeOut < mFadeFrames) {
                    sample = int32_t{mTail[channel]} * static_cast<int32_t>(mFadeFrames-mFadeOut-1) / static_cast<int32_t>(mFadeFrames);
                }
                output[i*mChannels + channel] = static_cast<int16_t>(sample);
                mLast[channel] = static_cast<int16_t>(sample);
            }
            if (!mPriming) {
                mRead = (mRead + 1) % mCapacity;
                --mCount;
                if (mFadeIn < mFadeFrames) ++mFadeIn;
            } else if (mFadeOut < mFadeFrames) ++mFadeOut;
        }
    }
  private:
    std::vector<int16_t> mData, mLast, mTail;
    uint32_t mChannels=0, mTarget=0, mCapacity=0, mRead=0, mCount=0;
    uint32_t mFadeFrames=1, mFadeIn=0, mFadeOut=1;
    uint64_t mUnderruns=0;
    bool mPriming=true;
};
}
