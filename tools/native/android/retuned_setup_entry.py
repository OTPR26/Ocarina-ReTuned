"""Embedded-Python entry point for Android's isolated preparation service."""
import os
from pathlib import Path
import sys


def prepare(kit_path, native_directory, rom_path, internal_root, userdata_root,
            cancel_path, callback):
    sys.dont_write_bytecode = True
    kit = Path(kit_path)
    os.environ['LIBCAPSTONE_PATH'] = native_directory
    sys.path[:0] = [str(kit / 'project/tools/native/android'),
                   str(kit / 'project/tools/native'), str(kit / 'project/src')]
    from rom_preparation import AndroidRomSetup
    from rom_setup import FileCancellation, SetupCancelled

    def progress(event):
        callback.progress(event['stage'], event['message'])

    try:
        worker = AndroidRomSetup(engine=kit / 'engine', ips=kit / 'hud.ips',
            elf=kit / 'hud.elf', sdk=kit / 'sdk',
            compiler=Path(native_directory) / 'libretuned_clang.so',
            linker=Path(native_directory) / 'libretuned_lld.so',
            runtime_library=Path(native_directory) / 'libc++_shared.so',
            progress=progress, cancel=FileCancellation(cancel_path),
            profile_root=userdata_root)
        worker.prepare(rom_path, internal_root)
        return True
    except SetupCancelled:
        callback.progress('cancelled', 'Setup cancelled. Your ROM and saves are unchanged.')
    except Exception as error:
        callback.progress('error', str(error) or 'Setup could not finish. Your ROM and saves are unchanged.')
    return False
