"""Offline report reproducibility and independent small-state math checks."""
import importlib.util
import itertools
import json
from pathlib import Path
import unittest
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('progression_bond', ROOT / 'scripts/analysis/progression_bond.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class ProgressionBondAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = a.analysis()

    def test_checked_in_output_and_report_are_current(self):
        self.assertEqual(self.result, json.loads((ROOT / 'tests/fixtures/progression-bond-analysis.json').read_text()))
        self.assertIn(a.markdown(self.result).strip(), (ROOT / 'docs/companion-progression-bond-analysis-v01.md').read_text())
        self.assertEqual(self.result, a.analysis())

    def test_renewal_matches_exhaustive_small_sequences(self):
        counts = {}
        for steps in itertools.product((1, 2, 3), repeat=5):
            total = 0
            for n, step in enumerate(steps, 1):
                total += step
                if total >= 5:
                    counts[n] = counts.get(n, 0) + 1
                    break
        self.assertEqual(a.hitting(5), {n: F(count, 3**5) for n, count in counts.items()})

    def test_gate_expectation_independent_small_closed_form(self):
        # EXP reaches one unit immediately, Bond target2 p1/2: negative binomial mean4.
        self.assertEqual(a.gate(1, 2, F(1,2))['expected_wins'], 4)
        self.assertEqual(a.gate(5, 1, F(1))['expected_wins'], float(a.expected(a.hitting(5))))
        self.assertIsNone(a.gate(5, 1, F(0))['expected_wins'])
        self.assertEqual(a.gate(5, 10, F(1))['expected_wins'], 10)

    def test_natural_gate_and_overshoot(self):
        dist = a.hitting(75)
        self.assertEqual((min(dist), max(dist)), (25, 75))
        self.assertEqual(self.result['sensitivity']['current']['nebla']['probability_locked_at_level'], 0)
        self.assertEqual(a.level(1499), 5)
        self.assertEqual(a.level(1500), 6)
        self.assertEqual(a.level(19000), 20)
        self.assertEqual(a.level(100000), 20)

    def test_capture_ignore_never_fabricate_progress(self):
        for pattern in ('C', 'I', 'CI'):
            result = a.simulate(pattern)
            self.assertEqual((result['level'], result['exp'], result['bond'], result['gold']), (1,0,0,0))
            self.assertIsNone(result['evolution_opportunity']['NEBLA'])
        self.assertEqual(a.simulate('W', 38)['stage'], 'NEBLA')
        self.assertEqual(a.simulate('WC', 75)['stage'], 'NEBLA')
        self.assertEqual(a.simulate('WIII', 149)['stage'], 'NEBLA')

    def test_berry_event_cost_effect_and_boundaries(self):
        rules = self.result['rules']
        for wins, case in self.result['berry_examples'].items():
            before, after = case['before'], case['after_one']
            self.assertEqual(after['bond'], before['bond']+1)
            self.assertEqual(after['gold'], before['gold']-30)
            self.assertEqual(after['exp'], before['exp'])
            self.assertEqual(after['stage'], before['stage'])
        with self.assertRaises(ValueError):
            a.buy_and_use_berry(a.state(0,0,0), 1, rules)
        with self.assertRaises(ValueError):
            a.buy_and_use_berry(a.state(1500,25,750), 100, rules)
        legacy = a.buy_and_use_berry(a.state(1500,11,30), 1, rules)
        self.assertEqual((legacy['stage'], legacy['bond'], legacy['gold']), ('NEBLA',12,0))

    def test_seed_roster_and_shop_authority(self):
        self.assertEqual(sum(m['weight'] for m in self.result['rules']['monsters']), 961)
        self.assertEqual(len(self.result['rules']['monsters']), 15)
        self.assertEqual(self.result['rules']['prices']['BOND_BERRY'], 30)


if __name__ == '__main__':
    unittest.main()
