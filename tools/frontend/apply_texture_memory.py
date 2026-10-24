"""Bound mobile replacement texture retention without freeing in-flight images."""
from pathlib import Path
from apply_native_port import edit


def apply(engine):
    root = Path(engine) / 'runtime/three_ds_recomp'
    source = Path(__file__).parent
    include = root / 'include/fast/oot3d'
    (include / 'retuned_texture_memory.h').write_text((source / 'texture_memory.h').read_text())
    (include / 'texture_memory_platform.h').write_text((source / 'texture_memory_platform.h').read_text())

    settings = include / 'graphics_settings.h'
    edit(settings, 'struct AzaharTexturePackSettings {\n',
         'struct AzaharTexturePackSettings {\n    bool AdaptiveTextureMemory = true;\n')
    persistence = root / 'src/fast/oot3d/graphics_settings_persistence.cpp'
    edit(persistence, '                  {"LoadDirectory",\n',
         '                  {"AdaptiveTextureMemory", settings.TexturePacks.Azahar.AdaptiveTextureMemory},\n'
         '                  {"LoadDirectory",\n')
    edit(persistence, '                if (version >= 9U) {\n',
         '                if (azahar->contains("AdaptiveTextureMemory"))\n'
         '                    ReadScalar(*azahar, "AdaptiveTextureMemory",\n'
         '                        result.Value.TexturePacks.Azahar.AdaptiveTextureMemory,\n'
         '                        "Graphics.TexturePacks.Azahar.AdaptiveTextureMemory", result);\n'
         '                if (version >= 9U) {\n')
    runtime = root / 'src/fast/oot3d/graphics_settings_runtime.cpp'
    marker = '#include "fast/oot3d/texture_memory_platform.h"'
    text = runtime.read_text()
    if marker not in text: runtime.write_text(marker + '\n' + text)
    marker = '#include "oot3d/renderer/azahar_texture_pack.h"'
    text = runtime.read_text()
    if marker not in text: runtime.write_text(marker + '\n' + text)
    edit(runtime, '    if (rewriteLoadedSettings && !mPersistenceSuppressed) {',
         '    RetunedFrontend::SetAdaptiveTextureMemory(mService.Current().TexturePacks.Azahar.AdaptiveTextureMemory);\n'
         '    if (rewriteLoadedSettings && !mPersistenceSuppressed) {')
    if 'mService.ConfirmCurrent();\n        RetunedFrontend::SetAdaptiveTextureMemory' not in runtime.read_text():
        edit(runtime, '        mService.ConfirmCurrent();\n        mSaveState',
             '        mService.ConfirmCurrent();\n'
             '        RetunedFrontend::SetAdaptiveTextureMemory(mService.Current().TexturePacks.Azahar.AdaptiveTextureMemory);\n'
             '        mSaveState')
    edit(runtime, '    auto result = mService.Stage(std::move(candidate), capabilities);',
         '    const bool previousAdaptiveTextureMemory = mService.Current().TexturePacks.Azahar.AdaptiveTextureMemory;\n'
         '    auto result = mService.Stage(std::move(candidate), capabilities);')
    edit(runtime, '        mSaveState = GraphicsSettingsSaveState::Pending;',
         '        if (previousAdaptiveTextureMemory != mService.Current().TexturePacks.Azahar.AdaptiveTextureMemory)\n'
         '            ::Oot3d::Renderer::AzaharTexturePackRuntime::Instance().Reload();\n'
         '        mSaveState = GraphicsSettingsSaveState::Pending;')

    def header(path):
        marker = '#include "fast/oot3d/retuned_texture_memory.h"'
        text = path.read_text()
        if marker not in text:
            path.write_text(marker + '\n' + text)

    loader = root / 'src/fast/oot3d/azahar_texture_pack.cpp'
    header(loader)
    edit(loader, '''    int channels = 0;
    stbi_uc* decoded =''', '''    int channels = 0;
    if (RetunedFrontend::LimitTextureMemory()) {
        if (!stbi_info_from_memory(input.data(), static_cast<int>(input.size()), &width, &height, &channels) ||
            width <= 0 || height <= 0)
            throw std::runtime_error("Invalid custom texture dimensions");
        const uint64_t bytes = uint64_t(width) * height * 4;
        const uint64_t limit = RetunedFrontend::TextureDecodeLimit(
            RetunedFrontend::DecodedTextureBudget(), RetunedFrontend::IsInterfaceTexture(hash));
        if (bytes > limit || !RetunedFrontend::HasTextureAllocationHeadroom(bytes * 2))
            throw std::runtime_error("Custom texture exceeds available memory; using original texture");
    }
    stbi_uc* decoded =''')
    text = loader.read_text()
    if '    void TrimDecodedTexturesLocked(' in text:
        start = text.index('    void TrimDecodedTexturesLocked(')
        end = text.index('    AzaharTextureResolveResult PollLocked(', start)
        text = text[:start] + (source / 'texture_memory_loader.cpp.inc').read_text() + text[end:]
        loader.write_text(text)
    else:
        edit(loader, '    AzaharTextureResolveResult PollLocked(uint64_t hash) const {',
             (source / 'texture_memory_loader.cpp.inc').read_text() +
             '    AzaharTextureResolveResult PollLocked(uint64_t hash) const {')
    edit(loader, '''    AzaharTextureResolveResult PollQueued(uint64_t hash) const {
        std::scoped_lock lock(mMutex);
        return PollLocked(hash);
    }''', '''    AzaharTextureResolveResult PollQueued(uint64_t hash) {
        std::scoped_lock lock(mMutex);
        if (RetunedFrontend::LimitTextureMemory() && mConfiguration.LoadCustomTextures &&
            !mReplacementCache.contains(hash) && !mFailedLoadHashes.contains(hash) &&
            !mPendingLoadGenerations.contains(hash) && mRetunedEvictedTextures.contains(hash)) {
            if (const auto indexed = mIndex.find(hash); indexed != mIndex.end()) {
                LoadJob job;
                job.Hash = hash;
                job.Generation = mGeneration;
                job.Texture = indexed->second;
                mPendingLoadGenerations.emplace(hash, mGeneration);
                mLoadJobs.push_back(std::move(job));
                ++mPendingLoads;
                mRetunedEvictedTextures.erase(hash);
                mWorkAvailable.notify_one();
            }
        }
        return PollLocked(hash);
    }''')
    edit(loader, '        if (!mConfigured || !mConfiguration.LoadCustomTextures) return {};\n        if (const auto cached = mReplacementCache.find(hash);',
         '        if (!mConfigured || !mConfiguration.LoadCustomTextures) return {};\n'
         '        if (RetunedFrontend::LimitTextureMemory() && mReplacementCache.contains(hash)) mRetunedTextureUse[hash] = ++mRetunedTextureClock;\n'
         '        if (const auto cached = mReplacementCache.find(hash);')
    edit(loader, '                if (replacement) mReplacementCache.insert_or_assign(job.Hash, std::move(replacement));',
         '                if (replacement) mReplacementCache.insert_or_assign(job.Hash, std::move(replacement));\n'
         '                TrimDecodedTexturesLocked(job.Hash);')
    if 'mRetunedTextureUse;' not in loader.read_text():
        edit(loader, '    mutable std::mutex mMutex;',
             '    mutable std::unordered_map<uint64_t, uint64_t> mRetunedTextureUse;\n'
             '    std::unordered_set<uint64_t> mRetunedEvictedTextures;\n'
             '    mutable uint64_t mRetunedTextureClock = 0;\n    mutable std::mutex mMutex;')
    # Hash lookups without a decoded result need no retained LRU entry.
    text = loader.read_text().replace(
        'if (RetunedFrontend::LimitTextureMemory()) mRetunedTextureUse[hash] = ++mRetunedTextureClock;',
        'if (RetunedFrontend::LimitTextureMemory() && mReplacementCache.contains(hash)) mRetunedTextureUse[hash] = ++mRetunedTextureClock;')
    loader.write_text(text)

    renderer = root / 'include/fast/backends/gfx_vulkan.h'
    edit(renderer, '        uint64_t CustomReplacementHash = 0;',
         '        uint64_t RetunedLastUsedFrame = 0;\n        uint64_t CustomReplacementHash = 0;')
    edit(renderer, '    std::map<NativePicaTextureKey, TextureRecord> mNativePicaTextures;',
         '    bool mRetunedTexturePressure = false;\n    std::map<NativePicaTextureKey, TextureRecord> mNativePicaTextures;')
    textures = root / 'src/fast/backends/gfx_vulkan_pica_textures.cpp'
    header(textures)
    edit(textures, '                if (!wasInserted) {\n                    return &inserted->second;',
         '                inserted->second.RetunedLastUsedFrame = mFrameCounter;\n'
         '                if (!wasInserted) {\n                    return &inserted->second;')
    edit(textures, '                if (record.Uploaded) {',
         '                record.RetunedLastUsedFrame = mFrameCounter;\n                if (record.Uploaded) {')
    edit(textures, '                record.CustomReplacementApplied = replacement;',
         '                record.CustomReplacementApplied = replacement;\n'
         '                if (RetunedFrontend::LimitTextureMemory() && replacement && RetunedFrontend::IsInterfaceTexture(replacementHash))\n'
         '                    std::fprintf(stderr, "RETUNED_INTERFACE_TEXTURE upload=%ux%u bytes=%llu\\n", width, height,\n'
         '                        static_cast<unsigned long long>(pixels.size()));')
    text = textures.read_text()
    marker = 'const bool memoryBudgetAvailable ='
    if marker not in text:
        original = 'const bool budgetAvailable =\n'
        assert text.count(original) == 2
        text = text.replace(original, '''const bool memoryBudgetAvailable = !RetunedFrontend::LimitTextureMemory() ||
                        RetunedFrontend::FitsTextureBudget(
                            RetunedFrontend::CacheBytes(mNativePicaTextures, [](const auto& entry) -> uint64_t {
                                return entry.second.CustomReplacementApplied ?
                                    uint64_t(entry.second.Width) * entry.second.Height * 4 : 0;
                            }), replacementBytes, RetunedFrontend::UploadedTextureBudget);
                    if (!memoryBudgetAvailable) mRetunedTexturePressure = true;
                    const bool budgetAvailable = memoryBudgetAvailable && (
''')
        text = text.replace('mCustomTextureUploadBytesThisFrame);', 'mCustomTextureUploadBytesThisFrame));')
        text = text.replace('std::min(kCustomTextureUploadBudgetBytes, mCustomTextureUploadBytesThisFrame));',
                            'std::min(kCustomTextureUploadBudgetBytes, mCustomTextureUploadBytesThisFrame);')
        textures.write_text(text)
    # Also account for images still waiting for an in-flight GPU fence.
    text = textures.read_text().replace(
        'std::min(kCustomTextureUploadBudgetBytes, mCustomTextureUploadBytesThisFrame));',
        'std::min(kCustomTextureUploadBudgetBytes, mCustomTextureUploadBytesThisFrame);')
    text = text.replace('RetunedFrontend::CacheBytes(mNativePicaTextures, [](const auto& entry) -> uint64_t {\n'
                        '                                return entry.second.CustomReplacementApplied ?\n'
                        '                                    uint64_t(entry.second.Width) * entry.second.Height * 4 : 0;\n'
                        '                            })',
                        'RetunedFrontend::UploadedTextureBytes(mNativePicaTextures, mFrameResources)')
    textures.write_text(text)
    text = textures.read_text()
    old = '''RetunedFrontend::FitsTextureBudget(
                            RetunedFrontend::UploadedTextureBytes(mNativePicaTextures, mFrameResources), replacementBytes, RetunedFrontend::UploadedTextureBudget)'''
    if old in text:
        assert text.count(old) == 2
        text = text.replace(old, 'RetunedFrontend::FitsReplacementBudget(mNativePicaTextures, mFrameResources, replacementBytes, resolved.NativeHash)', 1)
        text = text.replace(old, 'RetunedFrontend::FitsReplacementBudget(mNativePicaTextures, mFrameResources, replacementBytes, replacementResult.NativeHash)', 1)
    textures.write_text(text)
    frame = root / 'src/fast/backends/gfx_vulkan_frame.cpp'
    header(frame)
    text = frame.read_text()
    marker = '    if (RetunedFrontend::LimitTextureMemory()) {'
    end_marker = '    mCompletedNativePicaIds.insert(mCompletedNativePicaIds.end(),'
    if marker in text:
        start = text.index(marker)
        end = text.index(end_marker, start)
        text = text[:start] + (source / 'texture_memory_frame.cpp.inc').read_text() + text[end:]
        frame.write_text(text)
    else:
        edit(frame, end_marker, (source / 'texture_memory_frame.cpp.inc').read_text() + end_marker)
