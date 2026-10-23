"""Bounded Android compilation, cancellation, and deterministic linking."""
import importlib.util
import os
import sys
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'tools/native/android/rom_preparation.py'
spec = importlib.util.spec_from_file_location('android_parallel_preparation', MODULE)
android = importlib.util.module_from_spec(spec)
spec.loader.exec_module(android)


class AndroidParallelPreparation(unittest.TestCase):
    def test_memory_budget_keeps_small_and_unknown_devices_serial(self):
        gib = 1024 ** 3
        self.assertEqual(android.compilation_workers(8, 16*gib, 11*gib), 4)
        self.assertEqual(android.compilation_workers(8, 6*gib, 4*gib), 2)
        self.assertEqual(android.compilation_workers(8, 4*gib, 2*gib), 1)
        self.assertEqual(android.compilation_workers(8, 16*gib, 500*1024**2), 1)
        self.assertEqual(android.compilation_workers(8, 0, 0), 1)
        self.assertEqual(android.compilation_workers(1, 16*gib, 11*gib), 1)
        self.assertEqual(android.compilation_workers(8, 16*gib, 11*gib, 2), 2)

    def test_memory_probe_uses_available_and_handles_missing_kernel_fields(self):
        with patch.object(android.Path, 'read_text', return_value='MemTotal: 6291456 kB\nMemFree: 10 kB\nMemAvailable: 4194304 kB\n'):
            self.assertEqual(android.memory_snapshot(), (6*1024**3, 4*1024**3))
        for contents in ('MemTotal: 10 kB\n', 'MemTotal: invalid\nMemAvailable: 10 kB\n'):
            with patch.object(android.Path, 'read_text', return_value=contents):
                self.assertEqual(android.memory_snapshot(), (0, 0))
        with patch.object(android.Path, 'read_text', side_effect=PermissionError):
            self.assertEqual(android.memory_snapshot(), (0, 0))

    def fixture(self, root, mode='success'):
        generated = root / 'generated'
        generated.mkdir()
        for i in range(7):
            (generated / f'unit-{i}.cpp').write_text('fixture')
        events, lock = [], threading.Lock()
        class Worker(android.AndroidRomSetup):
            active = peak = 0
            linked = False
            launched = []
            def run(self, command, cwd=None):
                if command[0] != self.compiler:
                    self.linked = True
                    self.link_objects = [p.name for p in command if isinstance(p, Path) and p.suffix == '.o' and p.name[0].isdigit()]
                    Path(command[command.index('-o')+1]).write_bytes(b'linked')
                    return
                target = command[command.index('-o')+1]
                with lock:
                    self.active += 1
                    self.peak = max(self.peak, self.active)
                    self.launched.append(target.name)
                try:
                    if mode == 'fail' and target.name == '0.o':
                        time.sleep(.06)
                        raise android.SetupError('Original compiler failure')
                    duration = .12 if target.name == '0.o' else .04
                    if mode in ('fail', 'cancel'):
                        duration = 2
                    if self.cancel.wait(duration):
                        raise android.SetupError('Sibling stopped')
                    Path(target).write_bytes(b'object')
                finally:
                    with lock:
                        self.active -= 1
        worker = Worker(sdk=root/'sdk', engine=root/'engine', compiler=root/'compiler',
            linker=root/'linker', runtime_library=root/'runtime', ips=root/'mod.ips', elf=root/'mod.elf',
            progress=lambda event: events.append((threading.current_thread(), event)))
        worker.specification = dict(include_directories=[], sysroot='sysroot', resource_directory='resource',
            system_libraries='system', support_archive='support.a', builtins_archive='builtins.a', unwind_archive='unwind.a')
        return worker, generated, events

    @patch.object(android, 'memory_snapshot', return_value=(16*1024**3, 11*1024**3))
    @patch.object(android.os, 'cpu_count', return_value=8)
    def test_completed_progress_and_original_link_order(self, *_):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker, generated, events = self.fixture(root)
            original = worker.cancel
            self.assertTrue(worker.compile_title(root, generated).is_file())
            self.assertEqual(worker.peak, 4)
            self.assertEqual(worker.active, 0)
            self.assertEqual(worker.link_objects, [f'{i}.o' for i in range(8)])
            self.assertIs(worker.cancel, original)
            for i, (thread, event) in enumerate(events):
                self.assertIs(thread, threading.current_thread())
                self.assertIn(f'{i} of 8', event['message'])

    @patch.object(android, 'memory_snapshot', return_value=(16*1024**3, 11*1024**3))
    @patch.object(android.os, 'cpu_count', return_value=8)
    def test_failure_stops_and_joins_siblings_before_return(self, *_):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker, generated, _ = self.fixture(root, 'fail')
            original = worker.cancel
            started = time.monotonic()
            with self.assertRaisesRegex(android.SetupError, 'Original compiler failure'):
                worker.compile_title(root, generated)
            self.assertLess(time.monotonic()-started, 1)
            self.assertEqual(worker.active, 0)
            self.assertFalse(worker.linked)
            self.assertEqual(len(worker.launched), 4)
            self.assertIs(worker.cancel, original)
            self.assertFalse(original.is_set())

    @patch.object(android, 'memory_snapshot', return_value=(16*1024**3, 11*1024**3))
    @patch.object(android.os, 'cpu_count', return_value=8)
    def test_user_cancel_does_not_link_or_leave_workers(self, *_):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker, generated, _ = self.fixture(root, 'cancel')
            timer = threading.Timer(.06, worker.cancel.set)
            timer.start()
            try:
                with self.assertRaises(android.SetupError):
                    worker.compile_title(root, generated)
            finally:
                timer.join()
            self.assertEqual(worker.active, 0)
            self.assertFalse(worker.linked)
            self.assertTrue(worker.cancel.is_set())


class AndroidCompilerProcesses(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Android uses POSIX process groups')
    @patch.object(android, 'memory_snapshot', return_value=(16*1024**3, 11*1024**3))
    @patch.object(android.os, 'cpu_count', return_value=8)
    def test_real_failing_compiler_reaps_other_process_groups(self, *_):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker, generated, _ = AndroidParallelPreparation().fixture(root)
            script = root / 'compiler.py'
            script.write_text("import os,sys,time\nfrom pathlib import Path\n"
                "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                "time.sleep(.15)\n"
                "if sys.argv[2] == '0.o': sys.exit(2)\n"
                "time.sleep(20)\n")
            def run(command, cwd=None):
                self.assertEqual(command[0], worker.compiler, 'Link must not run after failure')
                target = command[command.index('-o')+1]
                return android.RomSetup.run(worker, [sys.executable, script, root/(target.name+'.pid'), target.name])
            worker.run = run
            with (root / 'setup.log').open('w') as worker.log:
                with self.assertRaises(android.SetupError):
                    worker.compile_title(root, generated)
            pids = list(root.glob('*.pid'))
            self.assertEqual(len(pids), 4)
            for pid_file in pids:
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), 0)
