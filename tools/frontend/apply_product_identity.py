"""Give packaged apps one product identity while retaining upstream ABI names."""
from pathlib import Path


def apply(engine):
    engine=Path(engine)
    runtime=engine/'tools/oot3d/native_game_runtime'
    for name in ('oot3d_environment_group.h','triaevum_oot3d_pica_host.cpp','triaevum_oot3d_pica_memory.cpp'):
        p=runtime/name
        s=p.read_text().replace('"TriAevum default (','"ReTuned default (')
        s=s.replace('"TriAevum PICA host','"Ocarina ReTuned renderer').replace('"TriAevum module has','"Ocarina ReTuned module has')
        p.write_text(s)
    bootstrap=runtime/'oot3d_native_game_bootstrap.cpp'
    bootstrap.write_text(bootstrap.read_text().replace('launch.Host.ApplicationId = "oot3d_native_game";', 'launch.Host.ApplicationId = "io.github.otpr26.ocarinaretuned";'))
    product=runtime/'triaevum_product_info.cpp';s=product.read_text()
    if '{"application_name", "Ocarina ReTuned"}' not in s:
        anchor='        {"runtime", "oot3d_native_game"},'
        if s.count(anchor)!=1:raise ValueError('Product identity context changed')
        s=s.replace(anchor,anchor+'\n        {"application_name", "Ocarina ReTuned"},\n        {"application_id", "io.github.otpr26.ocarinaretuned"},')
        product.write_text(s)
    p=engine/'CMake/oot3d/game.cmake';s=p.read_text()
    before='    set_property(TARGET oot3d_native_game PROPERTY OUTPUT_NAME TriAevum)'
    after='''    if(NOT ANDROID)
        set_property(TARGET oot3d_native_game PROPERTY OUTPUT_NAME OcarinaReTuned)
    else()
        # Keep the established Java/native loading contract for existing installs.
        set_property(TARGET oot3d_native_game PROPERTY OUTPUT_NAME TriAevum)
    endif()'''
    if after not in s:
        if s.count(before)!=1:raise ValueError('Product executable context changed')
        p.write_text(s.replace(before,after))

    resource=runtime/'retuned_windows.rc'
    resource.write_text(Path(__file__).with_name('retuned_windows.rc').read_text())
    cmake=engine/'CMake/oot3d/game.cmake';s=cmake.read_text()
    marker='# ReTuned product metadata in Explorer and Task Manager.'
    if marker not in s:
        s+='\n'+marker+'\nif(WIN32)\n    enable_language(RC)\n    target_sources(oot3d_native_game PRIVATE tools/oot3d/native_game_runtime/retuned_windows.rc)\nendif()\n'
        cmake.write_text(s)
