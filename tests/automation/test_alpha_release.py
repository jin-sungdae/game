import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('policy',ROOT/'scripts/alpha_release_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)

class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.code=policy.sources()
        self.baseline=json.loads((ROOT/'docs/evidence/alpha-release-runtime-inventory.json').read_text())
    def test_current_policy(self):
        self.assertEqual(policy.check(self.code,self.baseline),[])
    def test_focus_api_and_panel_regressions_fail(self):
        for value in ['makeKeyWindow','makeKeyAndOrderFront','activateIgnoringOtherApps']:
            code=dict(self.code);code['src-tauri/native/new.m']=value
            self.assertTrue(policy.check(code,self.baseline))
        self.code['src-tauri/native/panel.m']=self.code['src-tauri/native/panel.m'].replace('return NO','return YES')
        self.assertTrue(policy.check(self.code,self.baseline))
    def test_second_world_polling_queue_and_logging_regressions_fail(self):
        for value in ['std::thread::spawn(|| World::new())','setInterval(poll,1)','requestAnimationFrame(loop)','mpsc::channel()','eprintln!("password")']:
            code=dict(self.code);code['src-tauri/src/new.rs']=value
            self.assertTrue(policy.check(code,self.baseline))
        self.code['src-tauri/src/main.rs']=self.code['src-tauri/src/main.rs'].replace('tauri_plugin_single_instance::init(|_, _, _| {})','tauri_plugin_single_instance::init(|a, _, _| { a.show(); })')
        self.assertTrue(policy.check(self.code,self.baseline))
