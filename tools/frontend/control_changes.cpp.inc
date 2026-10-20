    if (mControlDraft != frameStartDraft) {
      std::string error;
      if (mControls->Apply(mControlDraft, &error)) {
        const auto saved = mControls->Snapshot();
        mControlDraft = saved.Config;
        mSavedControls = saved.Config;
        mObservedControlRevision = saved.Revision;
        mControlDirty = false;
        mStatus = "Saved";
      } else {
        mControlDirty = true;
        mStatus = std::move(error);
      }
    }
    if (mTopScreen && mTopDraft != frameStartTopDraft) {
      std::string error;
      if (mTopScreen->Apply(mTopDraft, &error)) {
        mTopDraft = mTopScreen->Snapshot().Config;
        mSavedTop = mTopDraft;
        mCameraDirty = false;
        if (!mControlDirty) mStatus = "Saved";
      } else {
        mCameraDirty = true;
        mStatus = std::move(error);
      }
    }
