from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from archive_links import validate_tar_links


def entry(name, target=None, directory=False):
    item = tarfile.TarInfo(name)
    if target is not None:
        item.type = tarfile.SYMTYPE
        item.linkname = target
    elif directory:
        item.type = tarfile.DIRTYPE
    return item


class ArchiveLinks(unittest.TestCase):
    def test_internal_compiler_aliases(self):
        validate_tar_links([entry('app', directory=True), entry('app/usr', directory=True),
            entry('app/usr/lib', directory=True), entry('app/usr/lib/loader'),
            entry('app/lib', 'usr/lib'), entry('app/loader', 'lib/loader')])

    def test_escaping_link_and_link_chain_are_rejected(self):
        for items in ([entry('link', '../outside')], [entry('link', '/outside')],
                      [entry('a', 'b'), entry('b', '../../outside')]):
            with self.assertRaises(ValueError):
                validate_tar_links(items)

    def test_cycles_and_missing_targets_are_rejected(self):
        for items in ([entry('a', 'b'), entry('b', 'a')], [entry('a', 'missing')]):
            with self.assertRaises(ValueError):
                validate_tar_links(items)

    def test_extraction_through_a_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'beneath'):
            validate_tar_links([entry('dir', directory=True), entry('alias', 'dir'), entry('alias/file')])

    def test_hardlinks_remain_rejected(self):
        hard = entry('alias')
        hard.type = tarfile.LNKTYPE
        hard.linkname = 'file'
        with self.assertRaises(ValueError):
            validate_tar_links([entry('file'), hard])
