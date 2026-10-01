import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('assets',ROOT/'scripts/validate_assets.py');assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)
class PuffFloating(unittest.TestCase):
    def test_original_delivery(self):self.assertEqual(assets.validate_puff_floating(ROOT),[])
    def test_missing_corrupt_filename_timing(self):
        for mode in ('missing','corrupt','filename','timing'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);d=root/'public/assets/monsters/puff';shutil.copytree(ROOT/'public/assets/monsters/puff',d);p=d/'float/float_03.png'
                if mode=='missing':p.unlink()
                if mode=='corrupt':p.write_bytes(b'bad png')
                if mode=='filename':p.rename(p.with_name('Float_03.png'))
                if mode=='timing':
                    p=d/'manifest.json';m=json.loads(p.read_text());m['animations']['float']['frameDuration']=100;p.write_text(json.dumps(m))
                self.assertTrue(assets.validate_puff_floating(root))
