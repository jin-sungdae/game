import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('input_evidence', ROOT / 'scripts/gui_qa/input_evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
analyze = module.analyze_trial


def trial(kind='transparent'):
    source = 'receiver' if kind == 'transparent' else 'luma-monitor'
    pid, window = (202, 22) if source == 'receiver' else (101, 11)
    events = [{'type': 'input', 'kind': k, 'source': source, 'wallTime': time,
               'uptime': time - 90, 'x': 30, 'y': 40, 'pid': pid, 'windowId': window, 'button': 0, 'targetPid': pid}
              for k, time in [('down', 102), ('up', 104)]]
    if kind == 'drag':
        events.insert(1, dict(events[0], kind='drag', wallTime=103, uptime=13, x=45))
        events[-1]['x'] = 50
    return {'version': 1, 'kind': kind, 'preflight': {'status': 'READY'},
            'coordinate': {'x': 30, 'y': 40, 'classification': kind, 'visualVerified': True,
                           'frameFile': 'frame.png', 'frameWallTime': 101.95},
            'events': events, 'actions': [] if source == 'receiver' else [{'kind': 'drag' if kind == 'drag' else 'interact', 'wallTime': 104.1}],
            'expectedButton': 0, 'expectedAction': 'drag' if kind == 'drag' else 'interact',
            'focus': {'complete': True, 'activations': 0, 'keyWindows': 0},
            'recording': {'complete': True, 'windowId': 11, 'frames': [{'file': 'frame.png' if i == 0 else f'frame-{i}.png', 'wallTime': 101.95+i*.1} for i in range(23)]},
            'identity': {'lumaPid': 101, 'lumaWindowId': 11, 'receiverPid': 202, 'receiverWindowId': 22},
            'interval': {'start': 100, 'end': 110},
            'coverage': {'complete': True, 'geometryStable': True, 'receiverFrontmost': True, 'monitorInstalled': True},
            'completed': True, 'runtimeSafe': True}


class InputEvidenceTest(unittest.TestCase):
    def status(self, value, expected):
        self.assertEqual(analyze(value)['status'], expected, analyze(value))

    def test_mixed_buttons_and_missing_target(self):
        value = trial()
        value['events'][1]['button'] = 1
        self.status(value, 'FAIL')
        value = trial()
        del value['events'][0]['targetPid']
        self.status(value, 'NOT_VERIFIED')

    def test_recording_stall_or_missing_tail_never_pass(self):
        value = trial()
        value['recording']['frames'] = value['recording']['frames'][:1]
        self.status(value, 'NOT_VERIFIED')
        value = trial()
        value['recording']['frames'] = [value['recording']['frames'][0], value['recording']['frames'][-1]]
        self.status(value, 'NOT_VERIFIED')

    def test_recorded_contracts_pass(self):
        for kind in ['transparent', 'character', 'button', 'drag']:
            with self.subTest(kind=kind):
                self.status(trial(kind), 'PASS')

    def test_focus_failure_overrides_incomplete_and_blocked(self):
        for key in ['activations', 'keyWindows']:
            value = trial()
            value['focus'].update({key: 1, 'complete': False})
            value['preflight']['status'] = 'GUI_ENVIRONMENT_BLOCKED'
            self.status(value, 'FAIL')

    def test_blocked_is_not_defect(self):
        value = trial()
        value['preflight']['status'] = 'GUI_ENVIRONMENT_BLOCKED'
        self.status(value, 'GUI_ENVIRONMENT_BLOCKED')

    def test_no_event_never_passes(self):
        value = trial()
        value['events'] = []
        self.status(value, 'NOT_VERIFIED')
        value['events'] = [dict(trial()['events'][0], type='heartbeat')]
        self.status(value, 'NOT_VERIFIED')

    def test_required_evidence_missing(self):
        for key in ['version', 'kind', 'preflight', 'coordinate', 'events', 'actions', 'focus', 'recording', 'identity', 'interval', 'coverage', 'completed', 'runtimeSafe']:
            value = trial()
            del value[key]
            with self.subTest(key=key):
                self.status(value, 'NOT_VERIFIED')

    def test_all_attestations_required(self):
        for section, key in [('coordinate', 'visualVerified'), ('focus', 'complete'), ('recording', 'complete'), ('coverage', 'complete'), ('coverage', 'geometryStable'), ('coverage', 'receiverFrontmost'), ('coverage', 'monitorInstalled')]:
            for bad in [False, None, 1, 'true']:
                value = trial()
                value[section][key] = bad
                self.status(value, 'NOT_VERIFIED')

    def test_nonfinite_and_bool_numbers_rejected(self):
        for bad in [float('nan'), float('inf'), float('-inf'), True, '102']:
            for section, key in [('coordinate', 'x'), ('coordinate', 'frameWallTime'), ('interval', 'start')]:
                value = trial()
                value[section][key] = bad
                self.status(value, 'NOT_VERIFIED')
            for key in ['wallTime', 'uptime', 'x', 'y', 'pid', 'windowId']:
                value = trial()
                value['events'][0][key] = bad
                self.status(value, 'NOT_VERIFIED')

    def test_identity_and_frame_mismatch_unverified(self):
        for key in ['pid', 'windowId']:
            value = trial()
            value['events'][0][key] = 999
            self.status(value, 'NOT_VERIFIED')
        value = trial()
        value['recording']['windowId'] = 99
        self.status(value, 'NOT_VERIFIED')
        value = trial()
        value['coordinate']['frameFile'] = 'other.png'
        self.status(value, 'NOT_VERIFIED')
        value = trial()
        value['coordinate']['x'] += 3
        self.status(value, 'NOT_VERIFIED')

    def test_reversed_intervals_and_events_unverified(self):
        value = trial()
        value['interval'] = {'start': 110, 'end': 100}
        self.status(value, 'NOT_VERIFIED')
        for key in ['wallTime', 'uptime']:
            value = trial()
            value['events'][0][key] = value['events'][1][key] + 1
            self.status(value, 'NOT_VERIFIED')
        value = trial()
        value['events'][0]['wallTime'] = 99
        self.status(value, 'NOT_VERIFIED')

    def test_wrong_target_and_duplicate_delivery_fail(self):
        value = trial()
        value['events'] = trial('character')['events']
        self.status(value, 'FAIL')
        value = trial('character')
        value['events'] += trial()['events']
        self.status(value, 'FAIL')
        value = trial()
        value['events'].append(copy.deepcopy(value['events'][0]))
        self.status(value, 'FAIL')

    def test_actions_exactly_match(self):
        value = trial()
        value['actions'] = [{'kind': 'drag', 'wallTime': 103}]
        self.status(value, 'FAIL')
        for actions in [[], [{'kind': 'wrong', 'wallTime': 103}], [{'kind': 'interact', 'wallTime': 103}] * 2]:
            value = trial('character')
            value['actions'] = actions
            self.status(value, 'FAIL')
        value = trial('character')
        value['actions'][0]['wallTime'] = 101
        self.status(value, 'NOT_VERIFIED')

    def test_drag_requires_real_drag_and_click_rejects_drag(self):
        value = trial('drag')
        value['events'] = [e for e in value['events'] if e['kind'] != 'drag']
        self.status(value, 'FAIL')
        value = trial('character')
        value['events'].insert(1, dict(value['events'][0], kind='drag', wallTime=103, uptime=13))
        self.status(value, 'FAIL')

    def test_boundary_is_characterization_by_default(self):
        value = trial('boundary')
        self.status(value, 'NOT_VERIFIED')
        value['expectedTarget'] = 'luma'
        self.status(value, 'NOT_VERIFIED')
        value['coordinate']['alphaEvidence'] = {'verified': True, 'alpha': 0.5}
        self.status(value, 'PASS')
        value['coordinate']['alphaEvidence']['alpha'] = 0
        self.status(value, 'PASS')
        value = trial()
        value['kind'] = value['coordinate']['classification'] = 'boundary'
        value['expectedTarget'] = 'receiver'
        value['coordinate']['alphaEvidence'] = {'verified': True, 'alpha': 0}
        self.status(value, 'PASS')

    def test_malformed_objects_never_raise(self):
        for value in [None, [], 'bad', 1, {}, {'version': 1, 'kind': []}]:
            self.status(value, 'NOT_VERIFIED')
        for section in ['preflight', 'coordinate', 'focus', 'recording', 'identity', 'interval', 'coverage']:
            for bad in [None, [], 'bad', 1]:
                value = trial()
                value[section] = bad
                self.status(value, 'NOT_VERIFIED')

    def test_frame_and_point_tolerances(self):
        for offset, expected in [(0.1, 'PASS'), (0.11, 'NOT_VERIFIED'), (-0.01, 'NOT_VERIFIED')]:
            value = trial()
            value['coordinate']['frameWallTime'] = 102 - offset
            value['recording']['frames'][0]['wallTime'] = 102 - offset
            self.status(value, expected)
        value = trial()
        value['coordinate']['x'] += 2
        self.status(value, 'PASS')
        value['coordinate']['y'] += 1
        self.status(value, 'NOT_VERIFIED')

    def test_schema_covers_contract(self):
        schema = json.loads((ROOT / 'scripts/gui_qa/input_evidence.schema.json').read_text())
        self.assertEqual(set(schema['required']), set(trial()) - {'expectedAction'})
        self.assertEqual(schema['properties']['kind']['enum'], ['transparent', 'character', 'boundary', 'button', 'drag'])
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['properties']['events']['items']['properties']['source']['enum'], ['receiver', 'luma-monitor'])


if __name__ == '__main__':
    unittest.main()
