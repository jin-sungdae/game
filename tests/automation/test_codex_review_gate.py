import copy
import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/ci'))
import codex_review
import codex_merge_gate


class ReviewGateTests(unittest.TestCase):
    def test_review_binds_exact_tested_patch(self):
        patch = b'patch'
        review = dict(status='PASS', head='a'*40, patchSha256=hashlib.sha256(patch).hexdigest(), risk='LOW', evidence=['file:1'])
        codex_review.verify(review, {'head': 'a'*40}, patch)
        for field, value in [('head', 'b'*40), ('status', 'CHANGES_REQUIRED'), ('risk', 'HIGH'), ('evidence', []), ('patchSha256', 'other')]:
            bad = dict(review, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                codex_review.verify(bad, {'head': 'a'*40}, patch)

    def evidence(self):
        head = 'a'*40
        result = {'head': head, 'review': {'head': head, 'status': 'PASS'}, 'files': ['tests/unit/test_example.py']}
        for field in ('ci', 'releaseGate', 'stackDependencies', 'branchProtection', 'productionApproval', 'repairBudget'):
            result[field] = {'head': head, 'status': 'PASS'}
        return result

    def test_dry_gate_never_merges(self):
        result = codex_merge_gate.decide(self.evidence())
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['mergeExecuted'])
        self.assertFalse(result['automaticMergeEnabled'])

    def test_every_evidence_gate_is_required_and_head_bound(self):
        for field in ('ci', 'releaseGate', 'stackDependencies', 'branchProtection', 'productionApproval', 'repairBudget', 'review'):
            for status, head in [('FAIL', 'a'*40), ('PENDING', 'a'*40), ('PASS', 'b'*40)]:
                evidence = copy.deepcopy(self.evidence())
                evidence[field] = {'status': status, 'head': head}
                with self.subTest(field=field, status=status, head=head):
                    self.assertEqual(codex_merge_gate.decide(evidence)['status'], 'FAIL')

    def test_missing_evidence_and_production_paths_block(self):
        self.assertEqual(codex_merge_gate.decide({})['status'], 'FAIL')
        for path in ('public/art.png', 'server/src/db.sql', 'src/balance.ts', '.github/workflows/test.yml'):
            evidence = self.evidence(); evidence['files'] = [path]
            self.assertIn('HUMAN_REVIEW_REQUIRED', codex_merge_gate.decide(evidence)['reasons'])
