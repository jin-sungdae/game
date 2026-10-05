import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('assets',ROOT/'scripts/validate_assets.py');assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)
class FloatingBatch(unittest.TestCase):
    def test_original_delivery(self):
        for code in ('WISP','LUNET'):
            with self.subTest(code=code):self.assertEqual(assets.validate_floating_batch(ROOT,code),[])
    def test_fail_closed(self):
        for code in ('WISP','LUNET'):
            for mode in ('missing','corrupt','filename','timing','hash','registration'):
                with self.subTest(code=code,mode=mode),tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp);d=root/'public/assets/monsters'/code.lower();shutil.copytree(ROOT/'public/assets/monsters'/code.lower(),d)
                    source=root/'docs/evidence/floating-alpha-batch-v1';source.mkdir(parents=True);shutil.copy(ROOT/'docs/evidence/floating-alpha-batch-v1/delivery-manifest.json',source)
                    p=d/'float/float_03.png'
                    if mode=='missing':p.unlink()
                    if mode=='corrupt':p.write_bytes(b'bad png')
                    if mode=='filename':p.rename(p.with_name('Float_03.png'))
                    if mode=='timing':
                        p=d/'manifest.json';m=json.loads(p.read_text());m['animations']['float']['frameDuration']=100;p.write_text(json.dumps(m))
                    if mode in ('hash','registration'):
                        p=source/'delivery-manifest.json';m=json.loads(p.read_text());f=m['characters'][code]['frames'][0];f['sha256' if mode=='hash' else 'cx']='bad' if mode=='hash' else 0;p.write_text(json.dumps(m))
                    self.assertTrue(assets.validate_floating_batch(root,code))
