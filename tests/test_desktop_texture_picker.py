import pathlib
import shutil
import subprocess
import tempfile
import unittest


class DesktopTexturePickerTests(unittest.TestCase):
    def test_navigation_unicode_cancellation_and_inaccessible_folders(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        include = pathlib.Path(__file__).resolve().parents[1] / 'tools/frontend'
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            pack = root / 'Texture pack 日本語'
            pack.mkdir()
            (pack / 'nested').mkdir()
            (pack / 'image.png').write_bytes(b'fixture')
            source = root / 'check.cpp'
            source.write_text('''#include "desktop_folder_model.h"
#include <cassert>
int main(int argc, char** argv) {
    using namespace RetunedFrontend::DesktopFolders;
    auto pack = Path(argv[1]);
    assert(Path(Text(pack)) == pack);
    Browser browser;
    browser.Begin(Text(pack));
    assert(browser.directory == pack && browser.CanSelect());
    assert(browser.listing.directories.size() == 1);
    assert(browser.listing.directories.front().filename() == "nested");
    auto saved = Text(pack);
    browser.Open(pack / "nested");
    assert(saved == Text(pack)); // Browsing/cancelling never changes the saved path.
    browser.Open(browser.directory.parent_path());
    assert(browser.directory == pack);
    browser.Open(pack / "missing");
    assert(!browser.CanSelect() && !browser.listing.error.empty());
    browser.Open(pack / "image.png");
    assert(!browser.CanSelect() && !browser.listing.error.empty());
    browser.Begin(saved);
    assert(browser.CanSelect() && Text(browser.directory) == saved);
    browser.Begin(Text(pack / "missing"));
    assert(browser.directory == Home());
}''')
            binary = root / 'check'
            subprocess.run([compiler, '-std=c++20', '-I'+str(include), str(source), '-o', str(binary)],
                           check=True, capture_output=True)
            subprocess.run([str(binary), str(pack)], check=True, capture_output=True)
