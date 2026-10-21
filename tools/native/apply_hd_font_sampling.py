"""Keep validated HD text coverage smooth without changing native samplers."""
from pathlib import Path


def apply(root):
    base = Path(root) / 'tools/oot3d/native_game_runtime'
    patches = [
        ('oot3d_native_pica_submission.h',
         '    std::vector<Fast::Renderer3ds::PicaTextureCopyReference> CopyReferences;\n\n    [[nodiscard]]',
         '    std::vector<Fast::Renderer3ds::PicaTextureCopyReference> CopyReferences;\n    // Presentation-only sampling for validated HD font coverage.\n    bool ReplacementLinearSampling = false;\n\n    [[nodiscard]]'),
        ('oot3d_native_hd_font_runtime.cpp',
         '    resource.ReplacementHeight = static_cast<std::uint16_t>(surface.Height * surface.Density);',
         '    resource.ReplacementHeight = static_cast<std::uint16_t>(surface.Height * surface.Density);\n    resource.ReplacementLinearSampling = true;'),
        ('oot3d_native_pica_vulkan_plan.cpp',
         '            textureBinding.State.Height = resource->ReplacementHeight;',
         '            textureBinding.State.Height = resource->ReplacementHeight;\n            if (resource->ReplacementLinearSampling) {\n                textureBinding.State.MinLinear = true;\n                textureBinding.State.MagLinear = true;\n            }'),
        ('oot3d_native_hd_font_runtime_tests.cpp',
         '        Check(texture.Width == 16 && atlas[0] == 0xff, "native state and memory unchanged");',
         '        Check(result.ReplacementLinearSampling && !texture.MinLinear && !texture.MagLinear,\n              "HD coverage requests smooth sampling without changing native sampler");\n        Check(!resolve(479).ReplacementLinearSampling, "native font retains its sampler");\n        Check(texture.Width == 16 && atlas[0] == 0xff, "native state and memory unchanged");'),
        ('oot3d_native_pica_vulkan_plan_tests.cpp',
         '    Oot3dNativeGame::Oot3dPicaVulkanDrawPlan consumingPlan;',
         '''    auto fontSamplingSubmission = consumingSubmission;
    fontSamplingSubmission.Resources.back().ReplacementWidth = 16U;
    fontSamplingSubmission.Resources.back().ReplacementHeight = 16U;
    fontSamplingSubmission.Resources.back().ReplacementLinearSampling = true;
    Oot3dNativeGame::Oot3dPicaVulkanDrawPlan fontSamplingPlan;
    Require(Oot3dNativeGame::BuildOot3dPicaVulkanDrawPlan(
                fontSamplingSubmission, fontSamplingPlan, &error), error);
    Require(fontSamplingPlan.Textures[0].State.MinLinear &&
                fontSamplingPlan.Textures[0].State.MagLinear &&
                !fontSamplingSubmission.State.Textures[0].MinLinear &&
                !fontSamplingSubmission.State.Textures[0].MagLinear,
            "HD font sampling override changed native texture state");
    Oot3dNativeGame::Oot3dPicaVulkanDrawPlan consumingPlan;'''),
        ('oot3d_native_pica_vulkan_plan_tests.cpp',
         '            "consuming Vulkan plan retained copied resource snapshots");',
         '            "consuming Vulkan plan retained copied resource snapshots");\n    Require(!consumingPlan.Textures[0].State.MinLinear &&\n                !consumingPlan.Textures[0].State.MagLinear,\n            "unmarked texture acquired HD font sampling");'),
    ]
    for name, before, after in patches:
        path = base/name
        text = path.read_text()
        if after in text:
            continue
        if text.count(before) != 1:
            raise ValueError('HD font sampling context changed: '+name)
        path.write_text(text.replace(before, after))
