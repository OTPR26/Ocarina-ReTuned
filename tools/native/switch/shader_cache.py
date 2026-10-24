"""Install local-only Switch GL program caching and warm-up integration."""
from pathlib import Path


def apply(engine):
    source=Path(__file__).resolve().parent
    engine=Path(engine)
    fragment=engine/'tools/oot3d/native_pica_frontend/oot3d_native_pica_fragment_shader_gen.cpp'
    fragment_text=fragment.read_text()
    if '// Structural specialization: disabled procedural textures' not in fragment_text:
        original='        source << Fast::Renderer3ds::PicaProcTexCode << Fast::Renderer3ds::PicaProcTexFragmentSampler;'
        replacement='#if defined(__SWITCH__)\n        // Structural specialization: disabled procedural textures need no interpreter.\n        // Enabled draws retain the complete procedural-texture implementation.\n        if (procTexEnabled && procTexReferenced) {\n            source << Fast::Renderer3ds::PicaProcTexCode << Fast::Renderer3ds::PicaProcTexFragmentSampler;\n        } else {\n            source << "vec4 pica_sample_proctex() { return vec4(0.0); }\\n";\n        }\n#else\n        source << Fast::Renderer3ds::PicaProcTexCode << Fast::Renderer3ds::PicaProcTexFragmentSampler;\n#endif'
        if fragment_text.count(original)!=1:raise ValueError('Procedural shader structural context changed')
        fragment.write_text(fragment_text.replace(original,replacement))
    header=engine/'runtime/three_ds_recomp/include/fast/renderer3ds/retuned_gl_program_cache.h'
    content=(source/'program_cache.h').read_text()
    if not header.exists() or header.read_text()!=content:header.write_text(content)
    compat=engine/'runtime/three_ds_recomp/include/fast/renderer3ds/retuned_switch_shader_compat.h'
    compat.write_text((source/'shader_compat.h').read_text())
    path=engine/'runtime/three_ds_recomp/src/fast/backends/gfx_opengl_pica.cpp'
    text=path.read_text()
    if '#include "fast/renderer3ds/retuned_gl_program_cache.h"' not in text:
        text=text.replace('#include <algorithm>','#include "fast/renderer3ds/retuned_gl_program_cache.h"\n#include <chrono>\n#include <cstdlib>\n#include <algorithm>',1)
    if '#include "fast/renderer3ds/retuned_switch_shader_compat.h"' not in text:
        text='#include "fast/renderer3ds/retuned_switch_shader_compat.h"\n'+text
    start=text.find('struct RetunedGlPrograms {')
    if start<0:start=text.index('PicaGlProgram BuildPicaGlProgram(')
    end=text.index('\nGLenum ToPicaGlCompare',start)
    text=text[:start]+(source/'program_cache.cpp.inc').read_text()+text[end:]
    if 'RetunedGlPrograms ProgramCache;' not in text:
        text=text.replace('    std::map<PicaGlShaderKey, PicaGlProgram> Programs;',
            '    std::map<PicaGlShaderKey, PicaGlProgram> Programs;\n    RetunedGlPrograms ProgramCache;',1)
        text=text.replace('    state.GeometryCacheEnabled = mNativePicaGeometryCacheEnabled;',
            '    state.GeometryCacheEnabled = mNativePicaGeometryCacheEnabled;\n    ConfigureRetunedGlPrograms(state.ProgramCache);',1)
        text=text.replace('BuildPicaGlProgram(draw)', 'BuildPicaGlProgram(draw,state.ProgramCache)')
        text=text.replace('    for (auto& [key, target] : state.Targets) {',
            '    for (const auto& [key,shader] : state.ProgramCache.Stages) glDeleteShader(shader);\n    for (auto& [key, target] : state.Targets) {',1)
        marker='    glDeleteShader(fragment);\n    glDeleteShader(vertex);\n#endif\n}\n\nvoid GfxRenderingAPIOGL::ShutdownNativePica'
        warm='''    glDeleteShader(fragment);
    glDeleteShader(vertex);
    // Rebuild/load previously encountered programs before entering gameplay.
    size_t prepared=0;uint64_t readBytes=0;
    std::error_code ec;
    if(!state.ProgramCache.Directory.empty()) {
        for(std::filesystem::directory_iterator i(state.ProgramCache.Directory,ec),end;
            !ec&&i!=end&&prepared<RetunedGlCache::MaxWarmPrograms;i.increment(ec)) {
            if(i->path().extension()!=".cache"||!i->is_regular_file(ec))continue;
            const auto bytes=i->file_size(ec);if(ec||readBytes+bytes>RetunedGlCache::MaxWarmBytes)break;
            readBytes+=bytes;RetunedGlCache::Record record;
            if(!RetunedGlCache::Load(i->path(),record))continue;
            GfxNativePicaDrawView draw{};draw.VertexShaderSource=record.Vertex;draw.FragmentShaderSource=record.Fragment;
            const PicaGlShaderKey key{Renderer3ds::IdentifyPicaShaderSource(record.Vertex),Renderer3ds::IdentifyPicaShaderSource(record.Fragment)};
            try {state.Programs.emplace(key,BuildPicaGlProgram(draw,state.ProgramCache));++prepared;}
            catch(const std::exception& error){std::printf("Switch GL prewarm skipped invalid program: %s\\n",error.what());}
            SDL_PumpEvents();
        }
    }
    std::printf("Switch GL prewarm complete: programs=%zu binary_hits=%zu source_builds=%zu\\n",prepared,state.ProgramCache.BinaryHits,state.ProgramCache.SourceBuilds);
#endif
}

void GfxRenderingAPIOGL::ShutdownNativePica'''
        if marker not in text:raise ValueError('GL initialization warm-up anchor changed')
        text=text.replace(marker,warm,1)
    if path.read_text()!=text:path.write_text(text)
