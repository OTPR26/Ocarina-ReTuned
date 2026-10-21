import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('open_font', ROOT / 'tools/native/prepare_open_font.py')
font = importlib.util.module_from_spec(spec)
spec.loader.exec_module(font)


class OpenFontTests(unittest.TestCase):
    def native(self, codes=(32, 65, 66)):
        header = b'QBF1' + struct.pack('<HHHH4B', len(codes), 2, 32, 0, 4, 32, 32, 2)
        # Two character labels deliberately share a native glyph pointer.
        directory = b''.join(struct.pack('<HH4B', code, 0 if code == 32 else 1, 3, 11, 0, 0) for code in codes)
        return header + directory + bytes(1024)

    def test_licensed_glyphs_pair_without_changing_layout_or_aliases(self):
        native = self.native()
        coverage = (ROOT / 'resources/fonts/ReTunedDialogue.qbf').read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'font.zip'
            manifest = font.pair(native, coverage, output, ROOT / 'resources/fonts/LICENSE.txt')
            with zipfile.ZipFile(output) as archive:
                record = manifest['fonts'][0]
                self.assertEqual(archive.read(record['native_file']), native)
                result = archive.read(record['coverage_file'])
                self.assertEqual(result[16:40], native[16:40])
                self.assertEqual(record['replacement_metric_differences'], 0)
                self.assertEqual(record['density'], 2)
                # Space is empty; the A/B alias shares independently rendered A.
                self.assertFalse(any(result[40:40 + 2048]))
                self.assertTrue(any(result[40 + 2048:]))
                self.assertIn(b'SIL OPEN FONT LICENSE', archive.read('licenses/ReTuned-Dialogue-OFL.txt'))
                self.assertEqual(json.loads(archive.read('manifest.json'))['name'], 'ReTuned Dialogue')

    def test_missing_character_does_not_activate_a_partial_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'font.zip'
            with self.assertRaisesRegex(ValueError, 'lacks character'):
                font.pair(self.native((32, 65, 0x400)), (ROOT / 'resources/fonts/ReTunedDialogue.qbf').read_bytes(),
                          output, ROOT / 'resources/fonts/LICENSE.txt')
            self.assertFalse(output.exists())

    def test_repertoire_includes_accents_punctuation_and_space(self):
        data = (ROOT / 'resources/fonts/ReTunedDialogue.qbf').read_bytes()
        records, _, _, width, height, offset = font.parse(data)
        codes = {r[0] for r in records}
        self.assertTrue({ord(c) for c in 'ÀéñöŒœŸ—“„€◆'} <= codes)
        self.assertEqual((width, height), (64, 64))
        self.assertFalse(any(data[offset:offset + 2048]))
        with self.assertRaises(ValueError):
            font.parse(data[:-1])

class NativeCellFitTests(unittest.TestCase):
    def test_narrow_character_uses_native_bearing_and_width_without_mutating_inputs(self):
        # A native narrow numeral: its layout width is four units, unlike a
        # typeface's tabular digit advance. Existing game metrics stay authoritative.
        alpha = [0] * (32 * 32)
        for y in range(7, 27):
            for x in range(9, 22):
                alpha[y * 32 + x] = 15
        native = bytes((alpha[i] << 4) | alpha[i + 1] for i in range(0, len(alpha), 2))
        coverage = (ROOT / 'resources/fonts/ReTunedDialogue.qbf').read_bytes()
        records, _, _, _, _, offset = font.parse(coverage)
        glyph = next(g for code, g, metrics in records if code == ord('1'))
        pixels = coverage[offset + glyph * 2048:offset + (glyph + 1) * 2048]
        before = native, pixels
        result = font.fit_glyph(native, 32, 32, pixels, 64, 64, bytes([6, 4, 0, 0]))
        points = [(i * 2 + j) for i, v in enumerate(result) for j, n in enumerate((v >> 4, v & 15)) if n]
        self.assertTrue(points)
        self.assertGreaterEqual(min(i % 64 for i in points), 23)
        self.assertLess(max(i % 64 for i in points), 37)
        self.assertLess(max(i // 64 for i in points), 64)
        self.assertEqual((native, pixels), before)

    def test_blank_native_character_stays_blank(self):
        self.assertEqual(font.fit_glyph(bytes(512), 32, 32, bytes([255]) * 2048,
                                      64, 64, bytes([6, 4, 0, 0])), bytes(2048))

    def test_apostrophe_stays_above_baseline_instead_of_becoming_a_comma(self):
        def rectangle(w, h, bounds):
            alpha = [0] * (w*h)
            for y in range(bounds[1], bounds[3]):
                for x in range(bounds[0], bounds[2]): alpha[y*w+x] = 15
            return bytes((alpha[i]<<4)|alpha[i+1] for i in range(0,len(alpha),2))
        original = rectangle(32,32,(10,5,16,12))
        coverage = rectangle(64,64,(26,13,34,25))
        result = font.fit_glyph(original,32,32,coverage,64,64,bytes([6,4,0,0]))
        ys = [((i*2+j)//64) for i,v in enumerate(result) for j,n in enumerate((v>>4,v&15)) if n]
        self.assertEqual((min(ys),max(ys)),(13,24))

    def test_ink_width_tracks_advance_instead_of_leaving_variable_empty_space(self):
        def rectangle(w,h,x0,y0,x1,y1):
            alpha=[0]*(w*h)
            for y in range(y0,y1):
                for x in range(x0,x1):alpha[y*w+x]=15
            return bytes((alpha[i]<<4)|alpha[i+1] for i in range(0,len(alpha),2))
        native=rectangle(32,32,5,7,25,27)
        coverage=rectangle(64,64,20,15,44,52)
        gaps=[]
        for bearing,advance in [(3,9),(5,7),(3,10),(6,3)]:
            result=font.fit_glyph(native,32,32,coverage,64,64,bytes([bearing,advance,0,0]))
            xs=[(i*2+j)%64 for i,v in enumerate(result) for j,n in enumerate((v>>4,v&15)) if n]
            self.assertEqual(max(xs)-min(xs)+1,advance*4-4)
            # Cancel the native left bearing as the game renderer does.
            right=max(xs)+1-bearing*4
            next_left=advance*4-1
            gaps.append(next_left-right)
        self.assertEqual(gaps,[4,4,4,4])

class MatchedTypefaceTests(unittest.TestCase):
    def test_native_and_hd_use_natural_advances_and_same_directory(self):
        try:
            from PIL import ImageFont
        except ImportError:
            self.skipTest('Build-time font rasterizer is not installed')
        with tempfile.TemporaryDirectory() as temporary:
            native, hd = Path(temporary)/'native.qbf', Path(temporary)/'hd.qbf'
            face_path = ROOT/'resources/fonts/InterfaceSans-Bold.ttf'
            face = ImageFont.truetype(str(face_path), 864)
            font.build_matched(face_path, native, hd)
            a, b = native.read_bytes(), hd.read_bytes()
            records, _, _, width, height, offset = font.parse(a)
            hd_records, _, _, hw, hh, ho = font.parse(b)
            self.assertEqual((width,height,hw,hh),(32,32,128,128))
            self.assertEqual(records,hd_records)
            for code,glyph,metrics in records:
                if code != 0x25c6:
                    self.assertEqual(metrics[1]+1-font.RIGHT_BEARING_ADJUSTMENTS.get(code,0),
                                     round(face.getlength(chr(code))/64))
                self.assertEqual(metrics[0],2)
            # Different widths are deliberate typeface proportions, not old ROM
            # advances or horizontal bitmap fitting.
            metrics = {chr(c):m for c,g,m in records}
            self.assertLess(metrics['i'][1],metrics['m'][1])
            self.assertLess(metrics['.'][1],metrics['W'][1])
            self.assertFalse(any(b[ho:ho+8192]))
            def ink_bounds(character):
                _,glyph,metric = next(r for r in hd_records if r[0]==ord(character))
                pixels=b[ho+glyph*8192:ho+(glyph+1)*8192]
                xs=[(i*2+j)%128 for i,v in enumerate(pixels)
                    for j,n in enumerate((v>>4,v&15)) if n]
                return min(xs),max(xs),metric
            _,t_right,t_metrics=ink_bounds('t')
            h_left,_,_=ink_bounds('h')
            self.assertGreaterEqual(h_left+(t_metrics[1]+1)*8-t_right,8,
                                    't crossbar must clear the h stem by one logical unit')
            for following in 'te':
                left,_,_=ink_bounds(following)
                self.assertGreater(left+(t_metrics[1]+1)*8-t_right,0)
            output=Path(temporary)/'font.zip'
            manifest=font.pair(a,b,output,ROOT/'resources/fonts/LICENSE.txt')
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read(manifest['fonts'][0]['native_file']),a)
                self.assertEqual(archive.read(manifest['fonts'][0]['coverage_file']),b)
            with self.assertRaises(ValueError):
                font.build_matched(face_path,native,hd)
            smaller_native, smaller_hd = Path(temporary)/'n64.qbf', Path(temporary)/'h64.qbf'
            font.build_matched(face_path,smaller_native,smaller_hd,coverage_size=64)
            self.assertEqual(font.parse(smaller_native.read_bytes())[0],records,
                             'Atlas density must not alter text layout')

class DialogueStylePackTests(unittest.TestCase):
    def test_both_approved_faces_and_source_identity_are_in_local_pack(self):
        directory=ROOT/'resources/fonts'
        styles=font.read_styles(directory)
        source=styles['regular']['native']
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'choices.zip'
            result=font.pair_styles(source,directory,out)
            self.assertEqual(result['default_style'],'bold')
            self.assertFalse(result['redistributable'])
            self.assertTrue(result['private_local_artifact'])
            self.assertEqual({f['style'] for f in result['fonts']},{'regular','bold'})
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(archive.read(result['native_sources'][0]),source)
                for record in result['fonts']:
                    self.assertEqual(archive.read(record['native_file']),styles[record['style']]['native'])
                    self.assertEqual(archive.read(record['coverage_file']),styles[record['style']]['coverage'])
                self.assertIn('licenses/ReTuned-Dialogue-OFL.txt',archive.namelist())
            with self.assertRaises(ValueError):font.pair_styles(source,directory,out)

    def test_incompatible_native_geometry_never_creates_choice_pack(self):
        source=bytearray(font.read_styles(ROOT/'resources/fonts')['bold']['native'])
        struct.pack_into('<H',source,8,ord('A')) # valid QBF, incompatible fallback
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'choices.zip'
            with self.assertRaisesRegex(ValueError,'incompatible'):
                font.pair_styles(bytes(source),ROOT/'resources/fonts',out)
            self.assertFalse(out.exists())
