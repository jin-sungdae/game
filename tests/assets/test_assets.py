import importlib.util
import json
import shutil
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validator', ROOT/'scripts/validate_assets.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

# Binary parser fixtures only; never written into production asset directories.
def png(width=256, height=256, color=6):
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data)&0xffffffff)
    channels = 4 if color == 6 else 3
    pixels = b'\0'*(height*(1+width*channels))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB',width,height,8,color,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'src/entities').mkdir(parents=True)
        shutil.copy(ROOT/'src/entities/companions.json', self.root/'src/entities/companions.json')
        shutil.copy(ROOT/'src/entities/monsters.json', self.root/'src/entities/monsters.json')
        # Missing-base cases must stay independent of delivered production files.
        shutil.copytree(ROOT/'public/assets', self.root/'public/assets',
                        ignore=shutil.ignore_patterns('base.png'))
        self.stage = self.root/'public/assets/creatures/moa/stage01'

    def errors(self, allow=True):
        return validator.validate(self.root, allow)[0]

    def fill(self):
        registry=json.loads((self.root/'src/entities/companions.json').read_text())
        for definition in registry.values():
            for url in definition['stages'].values():
                stage=(self.root/'public'/url.lstrip('/')).parent
                if not (stage/'manifest.json').exists(): continue
                for clip,count in validator.COUNTS.items():
                    for i in range(count):
                        (stage/clip/f'{clip}_{i:02}.png').write_bytes(png())

    def test_scaffold_pending_not_production_pass(self):
        errors,pending = validator.validate(self.root,True)
        self.assertEqual(errors,[])
        self.assertEqual(len(pending),25)
        self.assertTrue(self.errors(False))

    def test_complete_registered_frame_fixture(self):
        self.fill()
        self.assertEqual(validator.validate(self.root,True),([],["moa/stage03: asset not supplied"]))
        self.assertEqual(validator.validate(self.root)[0],["moa/stage03: asset not supplied"])

    def test_missing_manifest(self):
        (self.stage/'manifest.json').unlink()
        self.assertTrue(any('manifest' in e for e in self.errors()))

    def test_missing_directory(self):
        shutil.rmtree(self.stage/'idle')
        self.assertTrue(any('missing directory' in e for e in self.errors()))

    def test_invalid_manifest_frame_count(self):
        p=self.stage/'manifest.json';m=json.loads(p.read_text());m['animations']['idle']['frames']=7;p.write_text(json.dumps(m))
        self.assertTrue(any('invalid frame count' in e for e in self.errors()))

    def test_partial_clip_not_allowed(self):
        (self.stage/'idle/idle_00.png').write_bytes(png())
        self.assertTrue(any('missing frame idle_01.png' in e for e in self.errors()))
        self.assertTrue(any('frame count 1' in e for e in self.errors()))

    def test_filename_extension_and_numbering(self):
        for name in ('idle_6.png','idle_07.PNG','picture.jpg'):
            (self.stage/'idle'/name).write_bytes(png())
        self.assertTrue(any('invalid filename/numbering/extension' in e for e in self.errors()))

    def test_duplicate_index(self):
        for name in ('idle_00.png','idle_0.png'):
            (self.stage/'idle'/name).write_bytes(png())
        self.assertTrue(any('duplicate frame index' in e for e in self.errors()))

    def test_dimensions(self):
        p=self.stage/'idle/idle_00.png'
        for w,h in ((128,256),(256,128)):
            p.write_bytes(png(w,h))
            self.assertTrue(any('dimensions' in e for e in validator.png_errors(p)))

    def test_alpha(self):
        p=self.stage/'idle/idle_00.png';p.write_bytes(png(color=2))
        self.assertTrue(any('alpha channel' in e for e in validator.png_errors(p)))

    def test_corruption(self):
        p=self.stage/'idle/idle_00.png';p.write_bytes(png()[:-5])
        self.assertTrue(validator.png_errors(p))

    def test_manifest_identity(self):
        p=self.stage/'manifest.json';m=json.loads(p.read_text());m['species']='ruu';p.write_text(json.dumps(m))
        self.assertTrue(any('mismatch' in e for e in self.errors()))
