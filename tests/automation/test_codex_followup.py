import copy
import re
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/ci'))
import codex_followup as f

HEAD='a'*40
BASE='b'*40


def analysis(pr=1, head=HEAD, ci='PASS'):
    ledger={'schemaVersion':1,'repairIterations':0,'repairLimit':3,'artworkApproval':'HUMAN_REVIEW_REQUIRED',
            'nextTask':'connect ready idle','creatures':[{'creatureId':'M001','actions':[{'action':'IDLE','animationStatus':'ANIMATION_READY','runtimeStatus':'NOT_VERIFIED'}]}]}
    return {'pr':pr,'head':head,'base':BASE,'baseRef':'stacked-parent','ci':{'status':ci,'runs':[{'jobs':[{'name':'desktop-static','conclusion':'failure' if ci=='FAIL' else 'success'}]}]},
            'ledger':{'text':json.dumps(ledger)},'ledgerSummary':f.pipeline.ledger_summary({'status':'READ','text':json.dumps(ledger)})}


def state():
    return f.enroll(f.empty_state(),1,0,['src/ui/','tests/ui/'])


def ready(ticket):
    return {'status':'READY','taskId':ticket['choices'][0]['id'],'sourceEvidence':['src/ui/view.ts:12 actual caller'], 'runtimeEvidence':['caller -> view'], 'tests':['UI regression']}


class FollowupTests(unittest.TestCase):
    def test_dry_run_full_chain_and_draft_resume(self):
        original=state(); dry=copy.deepcopy(original)
        ticket=f.reserve(dry,analysis(),'run1',0)
        f.authorize(dry,ticket['key'],'run1',ready(ticket))
        self.assertEqual(dry['runs'][ticket['key']]['status'],'IMPLEMENTING')
        dry['runs'][ticket['key']]['status']='PUBLISHING'
        f.finish(dry,ticket['key'],'run1','PUBLISHED',2)
        self.assertEqual(dry['prs']['2'],{'root':'1','depth':1})
        self.assertEqual(dry['roots']['1']['attempts'],1)
        self.assertIsNone(dry['lock']);self.assertEqual(original['roots']['1']['attempts'],0)
        with self.assertRaisesRegex(ValueError,'DUPLICATE_TASK'):
            second=f.reserve(dry,analysis(2,'c'*40,'FAIL'),'run2',10)
            proposal=ready(second);proposal['taskId']=ticket['taskId']
            # A non-candidate task is rejected before task dedup; direct reservation already filters it.
            f.require(ticket['taskId'] not in dry['tasks'],'DUPLICATE_TASK')

    def test_duplicate_head_and_new_head_failure_counter(self):
        s=state();t=f.reserve(s,analysis(),'1',0);f.finish(s,t['key'],'1','FAILED')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_HEAD'):f.reserve(s,analysis(),'2',1)
        f.reserve(s,analysis(head='c'*40),'2',1)
        self.assertEqual(s['roots']['1']['attempts'],2)

    def test_ci_pending_and_failure_analysis_first(self):
        with self.assertRaisesRegex(ValueError,'CI_PENDING'):f.reserve(state(),analysis(ci='PENDING'),'1',0)
        ticket=f.reserve(state(),analysis(ci='FAIL'),'1',0)
        self.assertEqual(ticket['choices'][0]['kind'],'CI_REPAIR')

    def test_cross_pr_concurrency_and_owner(self):
        s=state();f.enroll(s,2,0,['src/ui/']);t=f.reserve(s,analysis(),'1',0)
        with self.assertRaisesRegex(ValueError,'CONCURRENT'):f.reserve(s,analysis(2),'2',10)
        with self.assertRaisesRegex(ValueError,'RUN_OWNER'):f.finish(s,t['key'],'wrong','FAILED')
        with self.assertRaisesRegex(ValueError,'CONCURRENT'):f.reserve(s,analysis(2),'2',999999)

    def test_pr_limit_chain_limit_and_daily_budget(self):
        s=state();s['roots']['1']['attempts']=3
        with self.assertRaisesRegex(ValueError,'REPAIR_LIMIT'):f.reserve(s,analysis(),'1',0)
        s=state();s['prs']['1']['depth']=3
        with self.assertRaisesRegex(ValueError,'CHAIN_LIMIT'):f.reserve(s,analysis(),'1',0)
        s=state();s['days']['1970-01-01']={'sessions':4,'modelInvocations':8}
        with self.assertRaisesRegex(ValueError,'DAILY_API'):f.reserve(s,analysis(),'1',0)

    def test_ledger_limit_cannot_be_reset_by_new_head(self):
        a=analysis();a['ledgerSummary']['repairIterations']=3
        with self.assertRaisesRegex(ValueError,'LEDGER_REPAIR_LIMIT'):f.reserve(state(),a,'1',0)
        with self.assertRaisesRegex(ValueError,'ENROLLMENT'):f.reserve(f.empty_state(),analysis(),'1',0)
        s=state()
        with self.assertRaisesRegex(ValueError,'NO_RESET'):f.enroll(s,1,0,['src/ui/'])

    def test_ai_failure_and_task_repeat_no_unbounded_retry(self):
        s=state();t=f.reserve(s,analysis(),'1',0)
        with self.assertRaisesRegex(ValueError,'AI_BLOCKED'):f.authorize(s,t['key'],'1',{'status':'BLOCKED'})
        f.authorize(s,t['key'],'1',ready(t));f.finish(s,t['key'],'1','FAILED')
        self.assertEqual(s['roots']['1']['attempts'],1)
        with self.assertRaisesRegex(ValueError,'NO_UNFINISHED'):f.reserve(s,analysis(head='c'*40),'2',5)

    def test_ambiguous_publication_preserves_lock(self):
        s=state();t=f.reserve(s,analysis(),'1',0);f.authorize(s,t['key'],'1',ready(t));t['status']='PUBLISHING'
        f.finish(s,t['key'],'1','FAILED');self.assertEqual(s['lock'],t['key']);self.assertEqual(t['status'],'PUBLICATION_UNKNOWN')
        f.finish(s,t['key'],'1','FAILED');self.assertEqual(s['lock'],t['key'])

    def test_production_assets_identity_approval_and_engine_guard(self):
        for path in ['public/a.png','.github/workflows/x.yml','AGENTS.md','src-tauri/src/movement.rs','server/src/main/java/dev/luma/game/BattleService.java','../escape','design/other.json']:
            self.assertTrue(f.protected(path),path)
        before=json.loads(analysis()['ledger']['text']);after=copy.deepcopy(before);after['nextTask']='next safe task';f.guard_ledger(before,after)
        for key,value in [('artworkApproval','APPROVED'),('repairIterations',-1),('fullProductionReady',True)]:
            bad=copy.deepcopy(after);bad[key]=value
            with self.assertRaisesRegex(ValueError,'APPROVAL_OR_IDENTITY'):f.guard_ledger(before,bad)

    def test_state_cas_no_retry(self):
        api=f.API('owner/repo');store=f.Store(api);store.sha='old'
        with patch.object(api,'put',side_effect=ValueError('STATE_CAS_OR_API_FAILED_NO_RETRY')) as put:
            with self.assertRaises(ValueError):store.save(state())
            self.assertEqual(put.call_count,1);self.assertEqual(put.call_args.args[1]['sha'],'old')

    def test_real_git_patch_and_approval_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            f.git(root,'init','-q')
            ledger=root/f.LEDGER;ledger.parent.mkdir(parents=True)
            before=json.loads(analysis()['ledger']['text'])
            ledger.write_text(json.dumps(before))
            code=root/'src/ui/view.ts';code.parent.mkdir(parents=True);code.write_text('export const connected = false;\n')
            f.git(root,'add','.')
            f.git(root,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
            ticket={'head':f.git(root,'rev-parse','HEAD').decode().strip(),'scope':['src/ui/'],'ledgerDigest':f.digest(before)}
            after=copy.deepcopy(before);after['nextTask']='verify next action';ledger.write_text(json.dumps(after))
            code.write_text('export const connected = true;\n')
            new=root/'src/ui/new.ts';new.write_text('export const value = 1;\n');f.git(root,'add','-N','.')
            patch=f.guard_patch(root,ticket)
            self.assertIn(b'new.ts',patch)
            after['artworkApproval']='APPROVED';ledger.write_text(json.dumps(after))
            with self.assertRaisesRegex(ValueError,'APPROVAL_OR_IDENTITY'):f.guard_patch(root,ticket)
            ledger.write_text(json.dumps(before));after['artworkApproval']=before['artworkApproval'];ledger.write_text(json.dumps(after))
            code.unlink()
            with self.assertRaisesRegex(ValueError,'DELETED_FILE'):f.guard_patch(root,ticket)

    def test_api_budget(self):
        api=f.API('owner/repo');api.requests=f.POLICY['maxGitHubRequests']
        with self.assertRaisesRegex(ValueError,'API_BUDGET'):api.charge()

    def test_single_pilot_requires_manual_matching_approved_pr(self):
        workflow=(ROOT/'.github/workflows/luma-codex-followup.yml').read_text()
        block=workflow.split('      - id: mode\n')[1].split('      - name:',1)[0].split('        run: |\n')[1]
        script='\n'.join(line[10:] for line in block.splitlines())
        for event,target,approved,expected in [('workflow_dispatch','123','123','true'),
                ('workflow_dispatch','124','123','false'),('workflow_run','123','123','false'),
                ('workflow_dispatch','','','false'),('workflow_dispatch','1;false','1;false','false')]:
            with self.subTest(event=event,target=target), tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'output'
                env={'PATH':'/usr/bin:/bin','GITHUB_OUTPUT':str(output),'EVENT_NAME':event,
                     'REQUESTED_MODE':'implement','ENABLED':'false','TEST_PR':target,'APPROVED_TEST_PR':approved}
                subprocess.run(['bash','-e','-c',script],env=env,check=True)
                self.assertEqual(output.read_text().strip(),'live='+expected)

    def test_workflow_uses_existing_action_and_separates_write_token(self):
        workflow=(ROOT/'.github/workflows/luma-codex-followup.yml').read_text()
        self.assertIn('LUMA PR watch (15 min)',workflow)
        self.assertIn('permission-profile:',workflow)
        self.assertNotIn('danger-full-access',workflow)
        self.assertNotIn('persist-credentials: true',workflow)
        self.assertNotIn('gh pr merge',workflow)
        for section in ['analyze','implement','validate']:
            body=re.split(r'\n  [a-z]+:\n', workflow.split('  '+section+':\n')[1], maxsplit=1)[0]
            self.assertNotIn('contents: write',body)
        self.assertIn('default: dry-run',workflow)
        self.assertIn('APPROVED_TEST_PR: ${{ vars.LUMA_CODEX_TEST_PR }}',workflow)
        self.assertIn('args+=(--pr "$TEST_PR")',workflow)
        self.assertIn('"$TEST_PR" == "$APPROVED_TEST_PR"',workflow)
        self.assertIn('environment: luma-codex-publish',workflow)


if __name__=='__main__':unittest.main()
