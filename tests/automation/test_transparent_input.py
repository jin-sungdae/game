"""Safety/regression tests for the QA orchestrator; no GUI or real processes."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/gui_qa'))
import transparent_input as qa


class OrchestratorTests(unittest.TestCase):
    def test_blocked_preflight_never_starts_session_or_receiver(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run'
            with patch.object(qa, 'preflight', return_value=(Path('/probe'), {'status': qa.BLOCKED, 'reason': 'NO_SAFE_CANDIDATE'})), patch.object(qa, 'run_trial', side_effect=AssertionError('must not launch')), patch.object(qa.sp, 'Popen', side_effect=AssertionError('must not start')):
                code = qa.main(['run', '--output', str(out), '--bundle', '/unused.app', '--bundle-revision', 'a'*40, '--kind', 'transparent', '--x', '20', '--y', '20'])
            self.assertEqual(code, 2)
            result = json.loads((out/'result.json').read_text())
            self.assertEqual(result['status'], qa.BLOCKED)
            self.assertEqual(result['userWindowMutations'], 0)
            self.assertFalse((out/'session').exists())

    def test_ready_preflight_alone_is_not_gui_pass(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(qa, 'preflight', return_value=(Path('/probe'), {'status': 'READY', 'reason': 'CANDIDATE_SPACE_OBSERVED'})), patch.object(qa, 'run_trial', side_effect=AssertionError('must not launch')):
                qa.main(['preflight', '--output', str(Path(d)/'probe')])
            self.assertEqual(json.loads((Path(d)/'probe/result.json').read_text())['status'], 'NOT_VERIFIED')

    def test_only_exact_owned_ids_excluded(self):
        raw = {'lumaProcessCount': 1, 'lumaWindows': [{'id': 10}, {'id': 11}], 'obstacles': [{'id': 20}, {'id': 21}]}
        old = copy.deepcopy(raw)
        clean = qa.sanitized_environment(raw, {10, 11}, 20)
        self.assertEqual(raw, old)
        self.assertEqual(clean['obstacles'], [{'id': 21}])
        self.assertEqual(clean['lumaProcessCount'], 0)
        for changed in [dict(raw, lumaProcessCount=2), dict(raw, lumaWindows=[{'id': 99}]), dict(raw, lumaWindows=[])]:
            with self.assertRaises(ValueError): qa.sanitized_environment(changed, {10, 11}, 20)

    def test_log_offset_does_not_recount_prior_actions(self):
        prefix = '[LUMA INPUT] drag\n'
        text = prefix+'LUMA_AUDIT {"pid":3,"event":"before-tauri","activations":0,"keyWindows":0}\n[LUMA INPUT] capture\n'
        actions, audit = qa.parse_luma(text, len(prefix))
        self.assertEqual(actions, ['capture'])
        self.assertEqual(audit[0]['event'], 'before-tauri')

    def test_outputs_cannot_modify_checkout(self):
        with self.assertRaises(ValueError): qa.output_directory(ROOT/'artifacts/new-test')
        with self.assertRaises(ValueError): qa.output_directory(ROOT)

    def test_malformed_interior_receiver_event_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'events.jsonl'
            path.write_text('{"type":"input"}\nBROKEN\n')
            with self.assertRaises(ValueError): qa.read_rows(path)
            path.write_text('{"type":"input"}\n{"unfinished":')
            self.assertEqual(qa.read_rows(path), [{'type':'input'}])
            with self.assertRaises(ValueError): qa.read_rows(path, final=True)

    def test_malformed_focus_audit_cannot_be_treated_as_zero(self):
        with self.assertRaises(ValueError): qa.parse_luma('LUMA_AUDIT broken\n', 0)

    def test_capture_uses_sample_time_not_callback_time(self):
        capture={'frames':[{'file':'a.png','wallTime':12.,'captureWallTime':10.5,'width':192,'height':208},
                           {'file':'b.png','wallTime':13.,'captureWallTime':9.5,'width':192,'height':208}]}
        rows=qa.capture_frames(capture,10.,11.)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['wallTime'],10.5)
        self.assertEqual(rows[0]['observedWallTime'],12.)
        with self.assertRaises(ValueError): qa.capture_frames({'frames':[{'wallTime':10.}]},9.,11.)

    def test_button_requires_explicit_expected_command(self):
        with self.assertRaises(SystemExit):
            qa.main(['run','--output','/unused','--bundle','/unused.app','--bundle-revision','a'*40,'--kind','button'])

    def test_status_exit_codes_never_report_unverified_as_success(self):
        self.assertEqual([qa.result_exit({'status':s}) for s in ['PASS','FAIL',qa.BLOCKED,'NOT_VERIFIED']], [0,1,2,3])

    def test_source_has_no_input_injection_or_user_app_operations(self):
        source = (ROOT/'scripts/gui_qa/transparent_input.py').read_text()
        native = (ROOT/'scripts/gui_qa/input_receiver.m').read_text()
        for bad in ['CGEventPost(', 'AXUIElementSetAttributeValue', 'AXUIElementPerformAction', 'activateIgnoringOtherApps', 'activateWithOptions', 'osascript', 'TextEdit']:
            self.assertNotIn(bad, source)
            self.assertNotIn(bad, native)
        for private in ['kAXValueAttribute', 'kAXTitleAttribute', 'kAXFocusedUIElementAttribute']:
            self.assertNotIn(private, native)

    def test_receiver_uses_production_app_not_replacement_webview(self):
        native = (ROOT/'scripts/gui_qa/input_receiver.m').read_text()
        for replacement in ['WKWebView alloc', 'NSPanel alloc', 'object_setClass']:
            self.assertNotIn(replacement, native)

    def test_point_containment_handles_negative_monitor_origin(self):
        self.assertTrue(qa.owned_contains([-1000, -50, 800, 600], (-500, 0)))
        self.assertFalse(qa.owned_contains([-1000, -50, 800, 600], (-200, 0)))


if __name__ == '__main__': unittest.main()
