struct RetunedGlPrograms {
    std::filesystem::path Directory;
    std::map<std::pair<GLenum,std::string>,GLuint> Stages;
    bool BinarySupported = false;
    uint64_t Bytes = 0;
    size_t Entries = 0, BinaryHits = 0, SourceBuilds = 0, StageBuilds = 0;
};

void ConfigureRetunedGlPrograms(RetunedGlPrograms& cache) {
    const char* path=std::getenv("TRIAEVUM_RENDERER_CACHE_DIR");
    if(!path || !*path) return;
    std::string driver;
    for(const auto name:{GL_VENDOR,GL_RENDERER,GL_VERSION,GL_SHADING_LANGUAGE_VERSION}) {
        const auto* value=glGetString(name);
        driver+=value?reinterpret_cast<const char*>(value):"unknown";
        driver+='\n';
    }
    // Bump this contract when shader rewriting or binary binding rules change.
    cache.Directory=std::filesystem::path(path)/"pica-gl-v2"/RetunedGlCache::Identity(driver);
    std::error_code ec;
    std::filesystem::create_directories(cache.Directory,ec);
    if(ec) { cache.Directory.clear();return; }
    for(std::filesystem::directory_iterator i(cache.Directory,ec),end;!ec&&i!=end;i.increment(ec)) {
        if(i->path().extension()!=".cache" || !i->is_regular_file(ec))continue;
        const auto bytes=i->file_size(ec);
        if(ec)break;
        ++cache.Entries;cache.Bytes+=bytes;
    }
    GLint formats=0;glGetIntegerv(GL_NUM_PROGRAM_BINARY_FORMATS,&formats);
    cache.BinarySupported = formats > 0;
    std::printf("Switch GL cache configured: files=%zu bytes=%llu binary_formats=%d\n",cache.Entries,
        static_cast<unsigned long long>(cache.Bytes),formats);
}

GLuint RetunedGlStage(RetunedGlPrograms& cache,GLenum type,std::string_view source) {
    const auto key=std::make_pair(type,RetunedGlCache::Identity(source));
    const auto found=cache.Stages.find(key);
    if(found!=cache.Stages.end())return found->second;
    const auto shader=CompilePicaGlShader(type,source);
    cache.Stages.emplace(key,shader);++cache.StageBuilds;
    return shader;
}

PicaGlProgram BuildPicaGlProgram(const GfxNativePicaDrawView& draw,RetunedGlPrograms& cache) {
    const auto started=std::chrono::steady_clock::now();
    RetunedGlCache::Record record{std::string(draw.VertexShaderSource),std::string(draw.FragmentShaderSource)};
    const auto file=cache.Directory/(RetunedGlCache::Key(record)+".cache");
    RetunedGlCache::Record disk;
    GLuint program=0U;
    double translateMs=0, compileMs=0, linkMs=0, diskMs=0;
    auto phase=std::chrono::steady_clock::now();
    const auto elapsed=[&] {
        const auto now=std::chrono::steady_clock::now();
        const double ms=std::chrono::duration<double,std::milli>(now-phase).count();
        phase=now;return ms;
    };
    bool binaryHit=false;
    const bool diskValid=!cache.Directory.empty()&&RetunedGlCache::Load(file,disk);
    diskMs+=elapsed();
    if(cache.BinarySupported&&diskValid&&!disk.Binary.empty()) {
        program=glCreateProgram();
        glProgramBinary(program,disk.Format,disk.Binary.data(),static_cast<GLsizei>(disk.Binary.size()));
        GLint linked=GL_FALSE;glGetProgramiv(program,GL_LINK_STATUS,&linked);
        if(linked==GL_TRUE) { binaryHit=true;++cache.BinaryHits; }
        else { glDeleteProgram(program);program=0;while(glGetError()!=GL_NO_ERROR){} }
    }
    if(!program) {
        std::string vertexSource,fragmentSource,error;
        if(!Renderer3ds::TranslatePicaShaderToOpenGl43(draw.VertexShaderSource,vertexSource,&error)||
           !Renderer3ds::TranslatePicaShaderToOpenGl43(draw.FragmentShaderSource,fragmentSource,&error))
            throw std::runtime_error("PICA GL translation failed: "+error);
        RetunedSwitchShader::Rewrite(fragmentSource);
        const auto mainName=fragmentSource.find("void main(");
        const auto mainBody=fragmentSource.find('{',mainName);
        if(mainName==std::string::npos||mainBody==std::string::npos)
            throw std::runtime_error("PICA fragment scissor injection has no main");
        fragmentSource.insert(mainBody+1,
            "\nif(retuned_exclude_scissor!=0 && all(greaterThanEqual(ivec2(gl_FragCoord.xy),retuned_exclude_bounds.xy)) && all(lessThan(ivec2(gl_FragCoord.xy),retuned_exclude_bounds.zw))) discard;\n");
        fragmentSource.insert(mainName,
            "uniform int retuned_exclude_scissor;\nuniform ivec4 retuned_exclude_bounds;\n");
        translateMs+=elapsed();
        const auto vertex=RetunedGlStage(cache,GL_VERTEX_SHADER,vertexSource);
        const auto fragment=RetunedGlStage(cache,GL_FRAGMENT_SHADER,fragmentSource);
        compileMs+=elapsed();
        program=glCreateProgram();
        if(cache.BinarySupported)glProgramParameteri(program,GL_PROGRAM_BINARY_RETRIEVABLE_HINT,GL_TRUE);
        glAttachShader(program,vertex);glAttachShader(program,fragment);glLinkProgram(program);
        GLint linked=GL_FALSE;glGetProgramiv(program,GL_LINK_STATUS,&linked);
        if(linked!=GL_TRUE) {
            GLint length=0;glGetProgramiv(program,GL_INFO_LOG_LENGTH,&length);
            std::string message(static_cast<size_t>(std::max(length,1)),'\0');
            glGetProgramInfoLog(program,length,nullptr,message.data());glDeleteProgram(program);
            throw std::runtime_error("PICA GL link failed: "+message);
        }
        linkMs+=elapsed();
        ++cache.SourceBuilds;
        // A corrupt/rejected cache only costs a rebuild; it never blocks play.
        GLint length=0;
        if(cache.BinarySupported)glGetProgramiv(program,GL_PROGRAM_BINARY_LENGTH,&length);
        if(length>0&&static_cast<uint32_t>(length)<=RetunedGlCache::MaxBinary) {
            record.Binary.resize(length);GLsizei actual=0;GLenum format=0;
            glGetProgramBinary(program,length,&actual,&format,record.Binary.data());
            record.Format=format;record.Binary.resize(std::max<GLsizei>(actual,0));
        }
        const auto estimate=record.Vertex.size()+record.Fragment.size()+record.Binary.size()+280;
        if(!diskValid&&!cache.Directory.empty()&&cache.Entries<RetunedGlCache::MaxWarmPrograms&&
           cache.Bytes+estimate<=RetunedGlCache::MaxWarmBytes) {
            if(RetunedGlCache::Store(cache.Directory,record)) {++cache.Entries;cache.Bytes+=estimate;}
            else std::puts("Switch GL cache write failed; rendering continues uncached");
        }
    }
    diskMs+=elapsed();
    glUseProgram(program);
    for(GLint slot=0;slot<3;++slot) {
        const auto name="pica_texture"+std::to_string(slot);
        glUniform1i(glGetUniformLocation(program,name.c_str()),slot+1);
    }
    glUniform1i(glGetUniformLocation(program,"pica_lighting_lut"),13);
    const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    std::printf("Switch GL program %s %.2fms source_builds=%zu binary_hits=%zu stage_builds=%zu translate_ms=%.2f compile_ms=%.2f link_ms=%.2f disk_ms=%.2f\n",
        binaryHit?"binary":"source",ms,cache.SourceBuilds,cache.BinaryHits,cache.StageBuilds,translateMs,compileMs,linkMs,diskMs);
    return {program,glGetUniformLocation(program,"retuned_exclude_scissor"),glGetUniformLocation(program,"retuned_exclude_bounds")};
}
