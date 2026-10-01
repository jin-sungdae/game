import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('assets',ROOT/'scripts/validate_assets.py');assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)
class MelloJump(unittest.TestCase):
    def test_original_delivery_integrity(self):
        self.assertEqual(assets.validate_mello_jump(ROOT),[])
    def test_missing_corrupt_wrong_name_and_metadata_fail_closed(self):
        for mode in ('missing','corrupt','filename','phase'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);d=root/'public/assets/monsters/mello';shutil.copytree(ROOT/'public/assets/monsters/mello',d)
                p=d/'jump/jump_04.png'
                if mode=='missing':p.unlink()
                if mode=='corrupt':p.write_bytes(b'invalid')
                if mode=='filename':p.rename(p.with_name('Jump_04.png'))
                if mode=='phase':
                    p=d/'manifest.json';m=json.loads(p.read_text());m['jumpPhases'].reverse();p.write_text(json.dumps(m))
                self.assertTrue(assets.validate_mello_jump(root))
