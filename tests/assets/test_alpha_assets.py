import json
import shutil
import struct
import subprocess
import sys
import zlib
import test_assets

validator = test_assets.validator

# Temporary binary parser fixtures; never production or placeholder assets.
def rgba_fixture(alpha=0, filtering=0):
    def chunk(kind, payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    row=bytes([20,40,60,alpha])*256
    previous=bytes(1024)
    raw=bytearray()
    for _ in range(256):
        raw.append(filtering)
        for i,value in enumerate(row):
            left=row[i-4] if i>=4 else 0
            above=previous[i]
            upper=previous[i-4] if i>=4 else 0
            p=left+above-upper
            distances=(abs(p-left),abs(p-above),abs(p-upper))
            predictor=[0,left,above,(left+above)//2,(left,above,upper)[distances.index(min(distances))]][filtering]
            raw.append((value-predictor)&255)
        previous=row
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

class AlphaAssetTests(test_assets.unittest.TestCase):
    setUp=test_assets.AssetTests.setUp

    def put(self,slug='mello',data=None,name='base.png'):
        p=self.root/f'public/assets/monsters/{slug}'/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(test_assets.png() if data is None else data)
        return p

    def test_optional_and_strict_fifteen_paths(self):
        errors,pending=validator.validate_alpha(self.root)
        self.assertEqual(errors,[]);self.assertEqual(len(pending),15)
        self.assertEqual(len(validator.validate_alpha(self.root,True)[0]),15)
        for slug in validator.ALPHA_CODES:self.put(slug)
        self.assertEqual(validator.validate_alpha(self.root,True),([],[]))
        # Companion assets remain absent; strict-alpha is independent.
        self.assertTrue(validator.validate_bases(self.root,True)[0])

    def test_actual_cli_strict_gate_missing_then_complete_delivery(self):
        command=[sys.executable,str(test_assets.ROOT/'scripts/validate_assets.py'),'--strict-alpha','--root',str(self.root)]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('/assets/monsters/mello/base.png: alpha base NOT_SUPPLIED',result.stdout)
        self.assertNotIn('/assets/creatures/',result.stdout)
        for slug in validator.ALPHA_CODES:self.put(slug)
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout)
        self.assertIn('0 errors; 0 unprovided assets',result.stdout)

    def test_invalid_dimensions_format_and_alpha_channel(self):
        for data,expected in [(test_assets.png(128,256),'dimensions'),(b'GIF89a','PNG'),(test_assets.png(color=2),'alpha channel')]:
            self.put(data=data)
            self.assertTrue(any(expected in e for e in validator.validate_alpha(self.root)[0]))

    def test_real_transparency_for_all_png_filters(self):
        for filtering in range(5):
            for alpha in (0,128,255):
                p=self.put(data=rgba_fixture(alpha,filtering))
                errors=validator.png_errors(p,require_transparency=True)
                self.assertEqual(bool(errors),alpha==255,(filtering,alpha,errors))

    def test_wrong_filename_duplicate_and_case(self):
        for name in ('base.PNG','Base.png','base-copy.png','monster.jpg'):
            p=self.put(name=name)
            self.assertTrue(any('filename' in e for e in validator.validate_alpha(self.root)[0]))
            p.unlink()
        self.put();self.put(name='base-copy.png')
        self.assertTrue(any('duplicate' in e for e in validator.validate_alpha(self.root)[0]))
        shutil.rmtree(self.root/'public/assets/monsters/mello')
        self.put(slug='MELLO')
        self.assertTrue(any('case mismatch' in e for e in validator.validate_alpha(self.root)[0]))

    def test_registry_scale_paths_and_duplicates(self):
        path=self.root/'src/entities/monsters.json'
        original=path.read_text()
        for value in [0,.49,1.51,True,'1',float('nan')]:
            data=json.loads(original);data['MELLO']['visualScale']=value;path.write_text(json.dumps(data))
            self.assertTrue(any('visualScale' in e for e in validator.validate_alpha(self.root)[0]))
        data=json.loads(original);data['MELLO']['baseAsset']='/assets/monsters/pip/base.png';path.write_text(json.dumps(data))
        self.assertTrue(any('path mismatch' in e for e in validator.validate_alpha(self.root)[0]))
        path.write_text(original.replace('"PIP": {','"PIP": {}, "PIP": {',1))
        self.assertTrue(any('duplicate registry key' in e for e in validator.validate_alpha(self.root)[0]))

    def test_only_canonical_pip_animation_manifest_is_allowed(self):
        manifest=json.loads((test_assets.ROOT/'public/assets/monsters/pip/manifest.json').read_text())
        p=self.put('pip',json.dumps(manifest).encode(),'manifest.json')
        self.assertEqual(validator.validate_alpha(self.root)[0],[])
        manifest['anchor']['x']=0
        p.write_text(json.dumps(manifest))
        self.assertTrue(any('pilot animation contract' in e for e in validator.validate_alpha(self.root)[0]))
        p.unlink()
        self.put('pip',b'{}','Manifest.json')
        self.assertTrue(any('invalid filename' in e for e in validator.validate_alpha(self.root)[0]))
