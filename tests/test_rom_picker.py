import pathlib
import shutil
import subprocess
import tempfile
import unittest


class RomPickerTests(unittest.TestCase):
    def test_local_listing_filters_sorts_and_rejects_missing_locations(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        header = pathlib.Path(__file__).resolve().parents[1] / 'tools/native/setup'
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root/'folder').mkdir()
            for name in ('z.CCI', 'a.3ds', 'not-a-rom.txt'):
                (root/name).write_bytes(b'fixture')
            source = root/'check.cpp'
            source.write_text('''#include "rom_picker.h"
#include <cassert>
int main(int argc,char** argv) {
    using namespace RetunedRomPicker;
    auto root=fs::path(argv[1]);auto listing=List(root);
    assert(listing.error.empty()&&!listing.truncated);
    assert(listing.entries.size()==3);
    assert(listing.entries[0].directory&&listing.entries[0].path.filename()=="folder");
    assert(listing.entries[1].path.filename()=="a.3ds");
    assert(listing.entries[2].path.filename()=="z.CCI");
    assert(IsRom(root/"z.CCI")&&!IsRom(root/"missing.cci")&&!IsRom(root/"folder"));
    assert(!List(root/"missing").error.empty());
    assert(!List(root/"a.3ds").error.empty());
}''')
            binary = root/'check'
            subprocess.run([compiler, '-std=c++20', '-I'+str(header), str(source), '-o', str(binary)],
                           check=True, capture_output=True)
            subprocess.run([str(binary), str(root)], check=True, capture_output=True)
