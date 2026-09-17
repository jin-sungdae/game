import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / 'ci' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load('repair_gate')
review = load('review_result')


class PolicyTests(unittest.TestCase):
    def test_only_three_reservations(self):
        for iteration in range(3):
            self.assertEqual(gate.decide('FAIL', iteration)['reserved_iteration'], iteration + 1)
        self.assertEqual(gate.decide('FAIL', 3), {
            'status': 'BLOCKED', 'next_action': 'HUMAN_REVIEW_REQUIRED', 'dispatch': False})

    def test_untrusted_missing_or_invalid_counter_fails_closed(self):
        for value in [None, -1, 4, '0', True]:
            self.assertEqual(gate.decide('FAIL', value)['status'], 'BLOCKED')

    def test_pass_and_protected_changes_never_dispatch(self):
        self.assertFalse(gate.decide('PASS', 0)['dispatch'])
        self.assertFalse(gate.decide('FAIL', 0, human_gate=True)['dispatch'])

    def test_protected_and_mass_deletion(self):
        self.assertTrue(review.human_paths([('M', 'src-tauri/vendor/tao/Cargo.toml')]))
        self.assertTrue(review.human_paths([('D', str(i)) for i in range(20)]))
        self.assertFalse(review.human_paths([('M', 'docs/example.md')]))

    def test_summary_missing_cancelled_job_is_not_pass(self):
        event = {'pull_request': {'number': 2, 'head': {'sha': 'a' * 40}, 'base': {'sha': 'b' * 40}}}
        for state in ['failure', 'cancelled', 'skipped', 'missing']:
            data = review.result({'desktop-static': {'result': 'success'}, 'macos-native': {'result': state}}, [], event, '1')
            self.assertEqual(data['status'], 'FAIL')
            self.assertFalse(data['automatic_dispatch'])
        data = review.result({j: {'result': 'success'} for j in ['desktop-static', 'macos-native']}, [], event, '1')
        self.assertEqual(data['next_action'], 'READY_FOR_HUMAN_REVIEW')
        self.assertEqual(data['checks'][-1]['status'], 'NOT_RUN')
        self.assertIsNone(data['iteration'])

    def test_ci_fixture(self):
        data = json.loads((ROOT / "tests/automation/fixture.json").read_text())
        self.assertEqual(data["auto_review_max_iterations"], 3)

    def test_foundation_contract(self):
        for file in ['AGENTS.md', 'docs/GAME_DESIGN.md', 'docs/ARCHITECTURE.md',
                     'docs/REVIEW_RULES.md', 'docs/DEVELOPMENT_WORKFLOW.md']:
            self.assertTrue((ROOT / file).is_file(), file)
        self.assertIn('AUTO_REVIEW_MAX_ITERATIONS=3', (ROOT / 'AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
