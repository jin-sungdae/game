"""Compile-time menu isolation and production/dev network policy regression."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ReleaseIsolation(unittest.TestCase):
    def test_native_menu_preprocessing(self):
        source = (ROOT / 'src-tauri/native/panel.m').read_text()
        # Only preprocess: AppKit declarations are irrelevant to conditional branches.
        source = source.replace('#import <AppKit/AppKit.h>', '')
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        def preprocess(debug):
            flags = ['-DLUMA_DEBUG_BUILD'] if debug else []
            return subprocess.check_output([compiler, '-E', '-P', '-x', 'c', *flags, '-'], input=source, text=True)
        release, debug = preprocess(False), preprocess(True)
        for token in ['Debug: Spawn PIP', 'Debug: Despawn PIP', '@selector(spawn:)', '@selector(despawn:)', 'pendingAction = 1', 'pendingAction = 2']:
            self.assertNotIn(token, release)
            self.assertIn(token, debug)
        self.assertIn('Quit LUMA', release)
        self.assertIn('pendingAction = 3', release)

    def test_every_debug_spawn_entry_is_compile_guarded(self):
        main = (ROOT / 'src-tauri/src/main.rs').read_text()
        calls = list(re.finditer(r'(?m)^.*=> world\.debug_spawn\(now\).*$', main))
        self.assertEqual(len(calls), 3)  # command, native menu, scripted smoke
        for call in calls:
            self.assertEqual(main[:call.start()].rstrip().splitlines()[-1].strip(), '#[cfg(debug_assertions)]')
        world = (ROOT / 'src-tauri/src/behaviors.rs').read_text()
        for method in ['debug_spawn', 'spawn']:
            self.assertRegex(world, r'#\[cfg\(any\(test, debug_assertions\)\)\]\s+pub fn ' + method + r'\(')

    def test_production_and_dev_csp_are_separate(self):
        security = json.loads((ROOT / 'src-tauri/tauri.conf.json').read_text())['app']['security']
        production, dev = security['csp'], security['devCsp']
        self.assertNotIn('localhost:1420', production)
        for origin in ['http://localhost:1420', 'ws://localhost:1420']:
            self.assertIn(origin, dev)
        for policy in [production, dev]:
            self.assertIn("script-src 'self'", policy)
            self.assertIn('connect-src ipc: http://ipc.localhost', policy)
            self.assertNotIn("'unsafe-eval'", policy)
