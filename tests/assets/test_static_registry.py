import importlib.util,json,shutil,tempfile,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('sync',ROOT/'scripts/sync_animation_manifests.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
class StaticRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'src/entities',self.root/'src/entities')
        for src in (ROOT/'public/assets').rglob('manifest.json'):
            dst=self.root/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dst)
        self.manifest=self.root/'public/assets/creatures/moa/stage01/manifest.json'
    def test_deterministic_and_fresh(self):
        self.assertEqual(sync.generate(self.root),sync.generate(self.root));self.assertEqual(sync.generate(self.root),(ROOT/'src/animation/generated-manifests.ts').read_text())
        m=json.loads(self.manifest.read_text());m['animations']['idle']['frameDuration']=250;self.manifest.write_text(json.dumps(m));self.assertNotEqual(sync.generate(self.root),sync.generate(ROOT))
    def test_invalid_and_required_missing_fail_closed(self):
        m=json.loads(self.manifest.read_text());m['species']='other';self.manifest.write_text(json.dumps(m))
        with self.assertRaises(ValueError):sync.generate(self.root)
        self.manifest.unlink()
        with self.assertRaises(ValueError):sync.generate(self.root)
    def test_optional_missing_no_invented_metadata(self):
        (self.root/'public/assets/monsters/pip/manifest.json').unlink();output=sync.generate(self.root);self.assertNotIn('/assets/monsters/pip/manifest.json',output);self.assertNotIn('/assets/creatures/moa/stage03/manifest.json',output)
    def test_external_path_and_duplicate_json_rejected(self):
        p=self.root/'src/entities/companions.json';m=json.loads(p.read_text());m['moa']['stages']['1']='https://example.invalid/manifest.json';p.write_text(json.dumps(m))
        with self.assertRaises(ValueError):sync.generate(self.root)
        with self.assertRaises(ValueError):sync.unique([('a',1),('a',2)])
    def test_csp_and_shared_clock_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT/'src-tauri/tauri.conf.json').read_bytes()).hexdigest(),'4505fc2a7a0bc3f0c7ac2724552f97572abd7f56d8631783913d8ea9288b2689')
        self.assertEqual(hashlib.sha256((ROOT/'src/animation/clock.ts').read_bytes()).hexdigest(),'261eaf8ed570aa9dba7aae3ae5b4f92056ac264fb0eaccb7a5acd9160af273c3')
