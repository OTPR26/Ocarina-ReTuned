from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from android_runtime import verify_runtime
from elf_fixture import elf


class AndroidRuntimeTests(unittest.TestCase):
    def test_missing_exception_runtime_is_rejected_and_matching_runtime_passes(self):
        required = ('__cxa_init_primary_exception',
                    '_ZNSt13exception_ptr31__from_native_exception_pointerEPv')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            host, runtime = root / 'host.so', root / 'runtime.so'
            host.write_bytes(elf(imports=required))
            runtime.write_bytes(elf())
            libraries = {'libTriAevum.so': host, 'libc++_shared.so': runtime}
            with self.assertRaisesRegex(ValueError, '__cxa_init_primary_exception'):
                verify_runtime(libraries)
            runtime.write_bytes(elf(exports=required))
            verify_runtime(libraries)

    def test_optional_symbols_and_system_abi_do_not_require_runtime_exports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            host, runtime = root / 'host.so', root / 'runtime.so'
            host.write_bytes(elf(imports=('__cxa_finalize',), weak=('__cxa_optional',)))
            runtime.write_bytes(elf())
            verify_runtime({'libTriAevum.so': host, 'libc++_shared.so': runtime})

    def test_non_elf_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'bad.so'
            path.write_bytes(b'not a library')
            with self.assertRaisesRegex(ValueError, 'ELF64'):
                verify_runtime({'libTriAevum.so': path, 'libc++_shared.so': path})
