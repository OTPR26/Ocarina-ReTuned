"""Switch OpenGL density and recoverable configuration replacement patches."""
from pathlib import Path


def apply_rendering(engine):
    path = Path(engine) / 'runtime/three_ds_recomp/src/fast/backends/gfx_opengl_pica.cpp'
    text = path.read_text()
    if 'kRetunedSwitchRenderScale' not in text:
        text = text.replace('namespace {\n', '''namespace {
// Guest addresses and image extents remain unscaled. Only colour/depth
// rasterization and display-transfer images have increased pixel density.
#if defined(__SWITCH__)
constexpr uint32_t kRetunedSwitchRenderScale = 3U;
#else
constexpr uint32_t kRetunedSwitchRenderScale = 1U;
#endif
''', 1)
        text = text.replace('key.Width, key.Height, 0,\n                     GL_RGBA',
            'key.Width * kRetunedSwitchRenderScale, key.Height * kRetunedSwitchRenderScale, 0,\n                     GL_RGBA',1)
        text = text.replace('                              key.Width, key.Height);',
            '                              key.Width * kRetunedSwitchRenderScale, key.Height * kRetunedSwitchRenderScale);',1)
        # Shadow image load/store remains at guest density to avoid duplicate
        # read/modify/write invocations racing on the same shadow texel.
        start = text.index('        glViewport(static_cast<GLint>(draw.ViewportX)')
        end = text.index('\n        const GLenum topology', start)
        text = text[:start] + '''        const uint32_t rasterScale = shadowProducer ? 1U : kRetunedSwitchRenderScale;
        glViewport(static_cast<GLint>(draw.ViewportX * rasterScale),
                   static_cast<GLint>(draw.ViewportY * rasterScale),
                   static_cast<GLsizei>(draw.ViewportWidth * rasterScale),
                   static_cast<GLsizei>(draw.ViewportHeight * rasterScale));
        glEnable(GL_SCISSOR_TEST);
        if (draw.ScissorMode == 3U) {
            glScissor(draw.ScissorX1 * rasterScale, draw.ScissorY1 * rasterScale,
                      (draw.ScissorX2 >= draw.ScissorX1 ? draw.ScissorX2 - draw.ScissorX1 + 1U : 0U) * rasterScale,
                      (draw.ScissorY2 >= draw.ScissorY1 ? draw.ScissorY2 - draw.ScissorY1 + 1U : 0U) * rasterScale);
        } else {
            glScissor(0, 0, draw.FramebufferWidth * rasterScale, draw.FramebufferHeight * rasterScale);
        }
''' + text[end:]
        # Transfer bounds are checked in guest pixels above this point. Preserve
        # density through the GPU copy rather than downsampling before scanout.
        text = text.replace('        const uint32_t outputWidth = std::max', '        uint32_t outputWidth = std::max',1)
        text = text.replace('        const uint32_t outputHeight = std::max', '        uint32_t outputHeight = std::max',1)
        text = text.replace('        auto& display = GetPicaGlDisplay(',
            '        outputWidth *= kRetunedSwitchRenderScale;\n'
            '        outputHeight *= kRetunedSwitchRenderScale;\n'
            '        auto& display = GetPicaGlDisplay(',1)
        path.write_text(text)

    text = path.read_text()
    if 'Switch PICA colour target' not in text:
        text = text.replace('#include <cmath>', '#include <cmath>\n#include <cstdio>')
        marker = '        glGenRenderbuffers(1, &target.DepthStencil);'
        text = text.replace(marker, '#if defined(__SWITCH__)\n        GLint actualWidth=0, actualHeight=0;\n        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&actualWidth);\n        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&actualHeight);\n        std::printf("Switch PICA colour target guest=%ux%u actual=%dx%d\\n", key.Width,key.Height,actualWidth,actualHeight);\n#endif\n' + marker, 1)
        path.write_text(text)

    path = Path(engine) / 'runtime/three_ds_recomp/src/ship/config/ConfigPersistence.cpp'
    text = path.read_text()
    if 'Switch SD rename cannot replace an existing file' not in text:
        marker = '#else\n    std::error_code replaceError;'
        replacement = '''#elif defined(__SWITCH__)
    // Switch SD rename cannot replace an existing file. Keep a recoverable
    // previous generation until the new generation has been installed.
    auto previous = target;
    previous += ".previous";
    std::error_code error;
    if (!std::filesystem::exists(target) && std::filesystem::exists(previous)) {
        std::filesystem::rename(previous, target, error);
        if (error) return {false, "unable to recover previous config: " + error.message()};
    }
    if (std::filesystem::exists(target)) {
        std::filesystem::remove(previous, error);
        if (error) return {false, "unable to clear previous config: " + error.message()};
        std::filesystem::rename(target, previous, error);
        if (error) return {false, "unable to retain previous config: " + error.message()};
    }
    std::filesystem::rename(temporary, target, error);
    if (error) {
        const auto failure = error.message();
        std::error_code rollback;
        if (std::filesystem::exists(previous)) std::filesystem::rename(previous, target, rollback);
        std::filesystem::remove(temporary, rollback);
        return {false, "unable to install config: " + failure};
    }
    std::filesystem::remove(previous, error);
#else
    std::error_code replaceError;'''
        if marker not in text:
            raise RuntimeError('config persistence patch anchor missing')
        path.write_text(text.replace(marker, replacement,1))


def apply_exclude_scissor(engine):
    path = Path(engine) / 'runtime/three_ds_recomp/src/fast/backends/gfx_opengl_pica.cpp'
    text = path.read_text()
    if 'retuned_exclude_scissor' in text:
        return
    text = text.replace('struct PicaGlProgram {\n    GLuint Handle = 0U;\n',
        'struct PicaGlProgram {\n    GLuint Handle = 0U;\n    GLint ExcludeScissor = -1;\n    GLint ExcludeBounds = -1;\n',1)
    marker = '    const GLuint vertex = CompilePicaGlShader(GL_VERTEX_SHADER, vertexSource);'
    injection = '''    // PICA mode 1 discards the inside of its inclusive rectangle. GL's
    // scissor test only supports keeping the inside, so use fragment discard.
    const auto firstLine = fragmentSource.find('\\n');
    const auto mainName = fragmentSource.find("void main(");
    const auto mainBody = fragmentSource.find('{', mainName);
    if(firstLine==std::string::npos || mainName==std::string::npos || mainBody==std::string::npos)
        throw std::runtime_error("PICA fragment scissor injection has no main");
    fragmentSource.insert(mainBody+1,
        "\\nif(retuned_exclude_scissor!=0 && all(greaterThanEqual(ivec2(gl_FragCoord.xy),retuned_exclude_bounds.xy)) && all(lessThan(ivec2(gl_FragCoord.xy),retuned_exclude_bounds.zw))) discard;\\n");
    fragmentSource.insert(mainName,
        "uniform int retuned_exclude_scissor;\\nuniform ivec4 retuned_exclude_bounds;\\n");
'''
    if marker not in text:
        raise RuntimeError('fragment scissor anchor missing')
    text = text.replace(marker,injection+marker,1)
    text = text.replace('    return {program};',
        '    return {program, glGetUniformLocation(program,"retuned_exclude_scissor"), glGetUniformLocation(program,"retuned_exclude_bounds")};',1)
    text = text.replace('''        if (draw.ScissorMode == 1U) {
            throw std::runtime_error("PICA exclude scissor requires shader emulation");
        }
''','',1)
    text = text.replace('if (draw.ScissorMode != 0U && draw.ScissorMode != 3U)',
        'if (draw.ScissorMode != 0U && draw.ScissorMode != 1U && draw.ScissorMode != 3U)',1)
    marker = '        const uint32_t rasterScale = shadowProducer ? 1U : kRetunedSwitchRenderScale;'
    text = text.replace(marker,marker+'''
        glUniform1i(program.ExcludeScissor,draw.ScissorMode==1U);
        glUniform4i(program.ExcludeBounds,draw.ScissorX1*rasterScale,draw.ScissorY1*rasterScale,
            (draw.ScissorX2+1U)*rasterScale,(draw.ScissorY2+1U)*rasterScale);
''',1)
    path.write_text(text)
