import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('assets',ROOT/'scripts/validate_assets.py');assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)
class NoctEdge(unittest.TestCase):
    def test_original_delivery(self):self.assertEqual(assets.validate_noct_edge(ROOT),[])
    def test_missing_corrupt_filename_timing_hash_registration(self):
        for mode in ('missing','corrupt','filename','timing','hash','registration'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);d=root/'public/assets/monsters/noct';shutil.copytree(ROOT/'public/assets/monsters/noct',d);p=d/'edge_move/edge_03.png'
                if mode=='missing':p.unlink()
                if mode=='corrupt':p.write_bytes(b'bad png')
                if mode=='filename':p.rename(p.with_name('Edge_03.png'))
                if mode=='timing':
                    p=d/'manifest.json';m=json.loads(p.read_text());m['animations']['edge_move']['frameDuration']=100;p.write_text(json.dumps(m))
                if mode in ('hash','registration'):
                    p=d/'delivery/manifest.json';m=json.loads(p.read_text());m['frames'][0]['sha256' if mode=='hash' else 'cx']='bad' if mode=='hash' else 0;p.write_text(json.dumps(m))
                self.assertTrue(assets.validate_noct_edge(root))
