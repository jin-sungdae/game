import copy
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import codex_followup as followup


class UnattendedSecurityTests(unittest.TestCase):
    def job(self, name):
        workflow = (ROOT / '.github/workflows/luma-codex-followup.yml').read_text()
        return re.split(r'\n  [a-z]+:\n', workflow.split('  ' + name + ':\n')[1], maxsplit=1)[0]

    def test_unattended_jobs_never_enter_human_approval_environments(self):
        # Same actor/reviewer cannot deadlock these jobs: neither protected
        # environment is referenced, and no approval API/bypass is introduced.
        for name in ('analyze', 'implement', 'review'):
            job = self.job(name)
            self.assertIn('environment: luma-codex-unattended', job)
            self.assertNotIn('environment: luma-codex-approval', job)
            self.assertIn('contents: read', job)
            self.assertNotIn('contents: write', job)
            self.assertNotIn('LUMA_AUTOMATION_APP_PRIVATE_KEY', job)
            self.assertNotIn('GH_TOKEN:', job)
            self.assertNotIn('create-github-app-token', job)
        self.assertNotIn('secrets.', self.job('validate'))

    def test_publication_token_is_after_read_only_preflight_and_scoped(self):
        job = self.job('publish')
        self.assertIn('environment: luma-codex-draft', job)
        self.assertLess(job.index('publication-preflight'), job.index('create-github-app-token'))
        self.assertIn('repositories: ${{ github.event.repository.name }}', job)
        self.assertIn('needs: [prepare, validate, review]', job)
        self.assertNotIn('npm ', job)
        self.assertNotIn('gh pr merge', job)
        self.assertNotIn('permission-administration:', job)
        self.assertNotIn('permission-secrets:', job)

    def test_high_risk_paths_cannot_enter_trusted_scope(self):
        for path in ('src/ui/AuthPanel.tsx', 'src/ui/permissions.ts', 'src/ui/security.ts',
                     'src/game/balance.ts', 'src/ui/reward.ts', 'src/ui/skill.ts',
                     'server/migration/V1.sql', 'public/art.png'):
            with self.subTest(path=path):
                self.assertTrue(followup.protected(path))
                self.assertFalse(followup.in_scope(path, ['src/ui/', 'src/game/', 'server/']))
        self.assertTrue(followup.in_scope('src/ui/tooltip.ts', ['src/ui/']))

    def test_publication_budget_and_task_ownership_are_rechecked(self):
        current = {'root': '1', 'attempt': 2, 'taskId': 'task', 'key': '1:head', 'depth': 1}
        state = {'roots': {'1': {'attempts': 2}}, 'tasks': {'task': {'key': '1:head'}}}
        followup.publication_limits(state, current)
        for count in (1, 3, 4):
            altered = copy.deepcopy(state); altered['roots']['1']['attempts'] = count
            with self.assertRaisesRegex(ValueError, 'REPAIR_LIMIT'):
                followup.publication_limits(altered, current)
        altered = copy.deepcopy(state); altered['tasks']['task']['key'] = 'other'
        with self.assertRaisesRegex(ValueError, 'TASK_OWNER'):
            followup.publication_limits(altered, current)
        with self.assertRaisesRegex(ValueError, 'CHAIN_LIMIT'):
            followup.publication_limits(state, dict(current, depth=3))

    def test_no_activation_or_protection_policy_mutation(self):
        workflow = (ROOT / '.github/workflows/luma-codex-followup.yml').read_text()
        self.assertNotIn('prevent_self_review: false', workflow)
        self.assertNotIn('pending_deployments', workflow)
        self.assertIn('default: dry-run', workflow)
        self.assertFalse(followup.POLICY['automaticMerge'])
