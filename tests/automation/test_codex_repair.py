import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import codex_followup as f
import codex_review as review
from test_codex_followup import analysis, HEAD, BASE


def sample():
    a = analysis()
    a.update(baseRef='main', protectedPaths=[], dependencyEvidence={'status': 'NOT_DECLARED'},
             files=[{'filename': 'src/ui/count.py', 'headContent': {'status': 'READ',
                     'text': 'def remaining(total, used):\n    return total - used + 1\n'}}])
    p = {'number': 1, 'state': 'open', 'head': {'sha': HEAD, 'ref': 'codex/owned', 'repo': {'full_name': 'owner/repo'}},
         'base': {'sha': BASE, 'ref': 'main'}, 'user': {'login': 'owner'},
         'labels': [{'name': 'luma-codex-owned'}], 'html_url': 'https://github.com/owner/repo/pull/1'}
    s = f.enroll(f.empty_state(), 1, 0, ['src/ui/', 'tests/ui/'])
    s['prs']['1']['repairIdentity'] = {'headRef':p['head']['ref'], 'author':'owner'}
    r = {'status': 'CHANGES_REQUIRED', 'head': HEAD, 'patchSha256': hashlib.sha256(b'diff').hexdigest(),
         'risk': 'LOW', 'evidence': ['remaining(5,2) returns 4'], 'findings': [
             {'path': 'src/ui/count.py', 'line': 2, 'quote': 'return total - used + 1',
              'reason': 'remaining count includes an extra item', 'tests': ['remaining(5,2) == 3'], 'confidence': 'CONFIRMED'}]}
    return s, a, p, r


class RepairTests(unittest.TestCase):
    def recorded(self):
        s, a, p, r = sample()
        f.record_review(s, a, r, b'diff', 'independent-review-1')
        return s, a, p, r

    def test_review_states_and_ci_failure_are_distinct(self):
        for status, expected in [('PASS', 'MERGE_READY'), ('CHANGES_REQUIRED', 'REPAIR_REQUIRED'),
                                 ('HUMAN_REVIEW_REQUIRED', 'HUMAN_REVIEW_REQUIRED'), ('BLOCKED', 'BLOCKED')]:
            s, a, p, r = sample(); r['status'] = status
            self.assertEqual(f.record_review(s, a, r, b'diff', 'review')['status'], expected)
            self.assertEqual(s['roots']['1']['attempts'], 0)
        s, a, p, r = sample(); a['ci']['status'] = 'FAIL'; r['status'] = 'PASS'
        self.assertEqual(f.record_review(s, a, r, b'diff', 'review')['status'], 'CI_FAILED')
        s, a, p, r = sample(); a['ci']['status'] = 'FAIL'
        self.assertEqual(f.record_review(s, a, r, b'diff', 'review')['ciStatus'], 'FAIL')

    def test_unverified_findings_stale_evidence_and_protected_changes(self):
        for field, value in [('confidence', 'UNVERIFIED'), ('quote', 'not in actual source'), ('line', 50), ('tests', [])]:
            s, a, p, r = sample(); r['findings'][0][field] = value
            self.assertEqual(review.decision(r, a, b'diff'), 'HUMAN_REVIEW_REQUIRED')
        s, a, p, r = sample(); a['protectedPaths'] = ['AGENTS.md']
        self.assertEqual(review.decision(r, a, b'diff'), 'HUMAN_REVIEW_REQUIRED')
        s, a, p, r = sample(); r['head'] = 'c' * 40
        with self.assertRaisesRegex(ValueError, 'HEAD_MISMATCH'): review.decision(r, a, b'diff')
        s, a, p, r = sample()
        with self.assertRaisesRegex(ValueError, 'PATCH_MISMATCH'): review.decision(r, a, b'other')

    def test_duplicate_and_independent_review_context(self):
        s, a, p, r = self.recorded()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_REVIEW'): f.record_review(s, a, r, b'diff', 'review2')
        s, a, p, r = sample(); s['prs']['1']['developerContext'] = 'same'
        with self.assertRaisesRegex(ValueError, 'INDEPENDENT_REVIEW'): f.record_review(s, a, r, b'diff', 'same')

    def test_handoff_prompt_and_same_pr_update_preserve_root_and_depth(self):
        s, a, p, r = self.recorded()
        t = f.reserve_repair(s, a, p, 'dev', 0)
        prompt = f.repair_prompt(t, a)
        for word in [HEAD, 'src/ui/', 'Release Gate', '변수명', '메서드명', 'commit', 'quote']:
            self.assertIn(word, prompt)
        self.assertEqual(t['operation'], 'REPAIR_EXISTING_PR')
        t['status'] = 'PUBLISHING'
        f.finish(s, t['key'], 'dev', 'UPDATED', 'c' * 40)
        self.assertEqual(s['prs']['1']['depth'], 0)
        self.assertEqual(list(s['prs']), ['1'])
        self.assertEqual(s['prs']['1']['nextAction'], 'WAIT_CI_THEN_INDEPENDENT_REVIEW')
        self.assertIsNone(s['lock'])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_HEAD'): f.reserve_repair(s, a, p, 'again', 1)
        # New HEAD requires another independently bound review, not the developer's report.
        a['head'] = 'c' * 40; p['head']['sha'] = a['head']; r.update(head=a['head'], status='PASS')
        self.assertEqual(f.record_review(s, a, r, b'diff', 'review2')['status'], 'MERGE_READY')

    def test_failed_attempts_are_charged_and_limit_does_not_reset(self):
        s, a, p, r = self.recorded()
        for index in range(3):
            t = f.reserve_repair(s, a, p, 'dev' + str(index), index * 86400)
            f.finish(s, t['key'], t['runId'], 'FAILED')
        self.assertEqual(s['roots']['1']['attempts'], 3)
        with self.assertRaisesRegex(ValueError, 'REPAIR_LIMIT'): f.reserve_repair(s, a, p, 'four', 4 * 86400)
        a['head'] = 'd' * 40; p['head']['sha'] = a['head']; r['head'] = a['head']
        f.record_review(s, a, r, b'diff', 'review2')
        with self.assertRaisesRegex(ValueError, 'REPAIR_LIMIT'): f.reserve_repair(s, a, p, 'five', 5 * 86400)

    def test_concurrent_session_scope_owner_and_daily_budget(self):
        for mutation, expected in [
            (lambda s,a,p: s.update(lock='another'), 'CONCURRENT'),
            (lambda s,a,p: p['user'].update(login='other'), 'OWNERSHIP'),
            (lambda s,a,p: s['roots']['1'].update(scope=['tests/ui/']), 'OUT_OF_SCOPE'),
            (lambda s,a,p: s['days'].update({'1970-01-01': {'sessions':4,'modelInvocations':8}}), 'DAILY_API'),
            (lambda s,a,p: a['ledgerSummary'].update(repairIterations=3), 'LEDGER_REPAIR_LIMIT'),
            (lambda s,a,p: a['ci'].update(status='PENDING'), 'CI_PENDING')]:
            s,a,p,r = self.recorded(); mutation(s,a,p)
            with self.assertRaisesRegex(ValueError, expected): f.reserve_repair(s,a,p,'dev',0)

    def test_stacked_dependency_is_not_a_prompt_claim(self):
        class API:
            repo = 'owner/repo'
            def get(self, path): return {'default_branch':'main'}
            def pages(self, path): return [{'merged_at':None}]
        a = sample()[1]; a['baseRef'] = 'stacked-parent'
        with self.assertRaisesRegex(ValueError, 'STACK_DEPENDENCY'): f.repair_dependencies(API(), a)
        a['baseRef'] = 'main'; f.repair_dependencies(API(), a)
        a['dependencyEvidence'] = {'merged':False}
        with self.assertRaisesRegex(ValueError, 'STACK_DEPENDENCY'): f.repair_dependencies(API(), a)

    def test_validation_is_bound_to_exact_patch_and_full_release(self):
        t = {'head':HEAD}; good = {'head':HEAD, 'patchSha256':hashlib.sha256(b'diff').hexdigest(),
                'status':'PASS','releaseGate':'AUTOMATED_READY','tests':['npm run validate:alpha:release']}
        f.repair_validation(good,t,b'diff')
        with self.assertRaisesRegex(ValueError,'PATCH_MISMATCH'): f.repair_validation(good,t,b'other')
        good['releaseGate']='NOT_RUN'
        with self.assertRaisesRegex(ValueError,'RELEASE_GATE'): f.repair_validation(good,t,b'diff')

    def test_production_ledger_without_counter_keeps_trusted_root_budget(self):
        s,a,p,r=self.recorded()
        a['ledger']['path']=f.pipeline.LEDGERS[1]
        a['ledgerSummary']['repairIterations']=None
        s['roots']['1']['attempts']=2
        t=f.reserve_repair(s,a,p,'dev',0)
        self.assertEqual(t['attempt'],3)
        f.finish(s,t['key'],'dev','FAILED')
        with self.assertRaisesRegex(ValueError,'REPAIR_LIMIT'): f.reserve_repair(s,a,p,'next',86400)

    def test_repair_dry_run_workflow_cannot_enable_paid_action(self):
        workflow=(ROOT/'.github/workflows/luma-codex-followup.yml').read_text()
        self.assertIn('prepare-repair --repo "$GH_REPO" --pr "$TEST_PR" --dry-run',workflow)
        self.assertIn("echo 'selected=false'",workflow)
        block=workflow.split('      - id: mode\n')[1].split('      - name:',1)[0].split('        run: |\n')[1]
        script='\n'.join(line[10:] for line in block.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output'
            env={'PATH':'/usr/bin:/bin','GITHUB_OUTPUT':str(output),'REQUESTED_MODE':'repair-dry-run',
                 'ENABLED':'true','EVENT_NAME':'workflow_dispatch','TEST_PR':'1','APPROVED_TEST_PR':'1'}
            subprocess.run(['bash','-e','-c',script],env=env,check=True)
            self.assertEqual(output.read_text().strip(),'live=false')

    def test_no_free_executor_does_not_reserve_attempt_or_call_model(self):
        s,a,p,r=self.recorded()
        class API:
            repo='owner/repo'
            def __init__(self,*args): pass
            def get(self,path): return p
        class Store:
            def __init__(self,*args): pass
            def load(self): return s
            def save(self,value): raise AssertionError('dry run cannot write state')
        with tempfile.TemporaryDirectory() as directory, patch.object(f,'API',API), patch.object(f,'Store',Store), \
             patch.object(f.pipeline,'ci',return_value=a['ci']), patch.object(f.pipeline,'analyze',return_value=a), \
             patch.object(sys,'argv',['f','prepare-repair','--repo','owner/repo','--pr','1','--dry-run','--output',directory+'/out']):
            f.main()
            result=json.loads(Path(directory+'/out/codex-request.json').read_text())
            self.assertEqual(result['reason'],'NO_SUPPORTED_NO_COST_EXECUTOR')
            self.assertEqual(result['modelCall'],'NOT_RUN')
            self.assertEqual(s['roots']['1']['attempts'],0)
            self.assertIsNone(s['lock'])

    def test_real_worktree_publish_same_branch_and_head_race(self):
        for race in (False, True):
            with self.subTest(race=race), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); repo=root/'repo'; repo.mkdir(); remote=root/'remote.git'
                f.git(root,'init','--bare','-q',str(remote)); f.git(repo,'init','-q','-b','main'); f.git(repo,'config','user.name','Test'); f.git(repo,'config','user.email','test@example.invalid')
                ledger=repo/f.LEDGER; ledger.parent.mkdir(parents=True)
                s,a,p,r=sample(); before=json.loads(a['ledger']['text']);ledger.write_text(json.dumps(before))
                code=repo/'src/ui/count.py';code.parent.mkdir(parents=True);code.write_text('def remaining(total, used):\n    return total - used\n')
                f.git(repo,'add','.'); f.git(repo,'-c','user.name=T','-c','user.email=t@example.invalid','commit','-qm','base')
                base=f.git(repo,'rev-parse','HEAD').decode().strip()
                f.git(repo,'checkout','-qb','codex/owned'); code.write_text('def remaining(total, used):\n    return total - used + 1\n')
                f.git(repo,'commit','-qam','introduced count regression'); head=f.git(repo,'rev-parse','HEAD').decode().strip()
                f.git(repo,'remote','add','origin',str(remote));f.git(repo,'push','-q','origin','main','codex/owned')
                source=root/'isolated';f.git(repo,'worktree','add','--detach',str(source),head)
                a.update(head=head,base=base);p['head']['sha']=head;p['base']['sha']=base;r['head']=head
                actual=f.git(source,'diff',base+'...'+head);r['patchSha256']=hashlib.sha256(actual).hexdigest()
                f.record_review(s,a,r,actual,'independent')
                t=f.reserve_repair(s,a,p,'dev',int(__import__('time').time()))
                check='from src.ui.count import remaining; assert remaining(5,2)==3'
                self.assertNotEqual(subprocess.run([sys.executable,'-c',check],cwd=source,capture_output=True).returncode,0)
                (source/'src/ui/count.py').write_text('def remaining(total, used):\n    return total - used\n')
                subprocess.run([sys.executable,'-c',check],cwd=source,check=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                # Remove interpreter caches from the intentionally isolated fixture only.
                for cache in source.rglob('__pycache__'): __import__('shutil').rmtree(cache)
                after=copy.deepcopy(before);after['nextTask']='independent review of updated PR';(source/f.LEDGER).write_text(json.dumps(after))
                raw=f.guard_patch(source,t);patch_file=root/'change.patch';patch_file.write_bytes(raw)
                f.git(source,'reset','--hard',head)
                for filename,value in [('ticket.json',t),('review.json',{'head':head,'status':'PASS','risk':'LOW',
                      'patchSha256':hashlib.sha256(raw).hexdigest(),'evidence':['independent fixture review']}),
                      ('validation.json',{'head':head,'patchSha256':hashlib.sha256(raw).hexdigest(),
                       'status':'PASS','releaseGate':'AUTOMATED_READY','tests':['npm run validate:alpha:release']})]:
                    (root/filename).write_text(json.dumps(value))
                # Validation JSON above is explicitly a fixture; actual release gate is run on this implementation separately.
                if race:
                    (repo/'other.txt').write_text('other session');f.git(repo,'add','other.txt');f.git(repo,'-c','user.name=T','-c','user.email=t@example.invalid','commit','-qm','concurrent change');f.git(repo,'push','-q','origin','codex/owned')
                class API:
                    repo='owner/repo'
                    def __init__(self,*args): pass
                    def get(self,path): return {'default_branch':'main'} if path=='' else p
                    def put(self,*args,**kwargs): raise AssertionError('repair must not create a PR')
                class Store:
                    def __init__(self,*args): pass
                    def load(self): return s
                    def save(self,value): pass
                argv=['f','publish','--repo','owner/repo','--source',str(source),'--ticket',str(root/'ticket.json'),
                      '--patch',str(patch_file),'--review',str(root/'review.json'),'--validation',str(root/'validation.json'),'--run-id','dev']
                with patch.object(f,'API',API),patch.object(f,'Store',Store),patch.object(f.pipeline,'ci',return_value=a['ci']),patch.object(f.pipeline,'analyze',return_value=a),patch.object(sys,'argv',argv):
                    if race:
                        with self.assertRaisesRegex(ValueError,'REMOTE_HEAD_CHANGED'): f.main()
                        self.assertEqual(t['status'],'CONFLICT');self.assertIsNone(s['lock'])
                    else:
                        f.main(); self.assertEqual(t['status'],'UPDATED')
                        updated=f.git(source,'rev-parse','HEAD').decode().strip()
                        self.assertEqual(f.git(repo,'ls-remote','origin','refs/heads/codex/owned').decode().split()[0],updated)
                        self.assertEqual(f.git(source,'rev-parse','HEAD^').decode().strip(),head)
                        self.assertEqual(list(s['prs']),['1'])


if __name__ == '__main__': unittest.main()
