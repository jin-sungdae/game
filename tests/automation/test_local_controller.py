import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/local-controller'))
import engine
import repair

class LocalControllerTests(unittest.TestCase):
    def result(self,status='PASS'):
        return {'status':status,'head':'a'*40,'reason':'검증 근거','files':[],'tests':[]}
    def test_parse_fail_closed(self):
        for value in ['PASS', '{}', self.result('APPROVED'), {**self.result(),'head':'b'*40}, {**self.result(),'reason':''}]:
            with self.assertRaises((ValueError,TypeError)): engine.normalize(value,'a'*40)
    def test_four_statuses_and_repair_scope(self):
        for status in engine.STATUSES:
            result={**self.result(status),'files':['src/example.ts'],'tests':['regression']}
            self.assertEqual(status,engine.normalize(json.dumps(result),'a'*40)['status'])
        with self.assertRaises(ValueError): engine.normalize(self.result('CHANGES_REQUIRED'),'a'*40)
    def test_no_paid_or_github_credentials_in_child_environment(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'secret','CODEX_API_KEY':'secret','GH_TOKEN':'secret','NODE_OPTIONS':'evil','BASH_ENV':'evil','CODEX_ACCESS_TOKEN':'secret'}):
            env=engine.clean_env()
            self.assertFalse(set(env)&{'OPENAI_API_KEY','CODEX_API_KEY','GH_TOKEN','NODE_OPTIONS','BASH_ENV','CODEX_ACCESS_TOKEN'})
    def fixtures(self):
        a={'head':'a'*40,'base':'b'*40,'pr':1,'ci':{'status':'PASS'},'dependencyEvidence':{'status':'NOT_DECLARED'}}
        p={'head':{'sha':'a'*40},'base':{'sha':'b'*40},'state':'open','mergeable':True,'mergeable_state':'clean','draft':False}
        r={'head':'a'*40,'workingTreeDirty':False,'status':'AUTOMATED_READY','checks':[{'status':'PASS'}]*18}
        s={'prs':{'1':{'root':'1'}},'roots':{'1':{'attempts':1}},'lock':None}
        return a,p,r,s
    def test_merge_requires_independent_exact_evidence_and_human_approval(self):
        a,p,r,s=self.fixtures()
        self.assertFalse(engine.merge_gate(a,self.result(),r,p,s)['eligible'])
        self.assertTrue(engine.merge_gate(a,self.result(),r,p,s,True)['eligible'])
        for field,value in [('head','c'*40),('workingTreeDirty',True),('checks',[])]:
            self.assertFalse(engine.merge_gate(a,self.result(),{**r,field:value},p,s,True)['eligible'])
        self.assertFalse(engine.merge_gate(a,self.result(),r,{**p,'draft':True},s,True)['eligible'])
        self.assertFalse(engine.merge_gate(a,self.result(),r,p,{**s,'lock':'other'},True)['eligible'])
    def test_pending_dependency_and_head_change_block(self):
        a,p,r,s=self.fixtures()
        for modified in [{**a,'ci':{'status':'PENDING'}},{**a,'dependencyEvidence':{'merged':False}},{**a,'head':'c'*40}]:
            self.assertFalse(engine.merge_gate(modified,self.result(),r,p,s,True)['eligible'])
    def test_next_task_reuses_ledger_filter_and_completed_tasks(self):
        a={'pr':1,'ci':{'status':'PASS'},'ledgerSummary':{'status':'READ_UNTRUSTED','repairIterations':0,'incomplete':[
            {'creatureId':'X','action':'IDLE','animationStatus':'ANIMATION_READY','runtimeStatus':'NOT_CONNECTED'},
            {'creatureId':'Y','action':'IDLE','animationStatus':'NOT_SUPPLIED','runtimeStatus':'NOT_CONNECTED'}]}}
        s={'prs':{'1':{'root':'1'}},'tasks':{}}
        result=engine.next_tasks(a,s);self.assertEqual(1,len(result['tasks']))
        s['tasks'][result['tasks'][0]['id']]={'status':'UPDATED'}
        self.assertEqual([],engine.next_tasks(a,s)['tasks'])
        self.assertEqual('BLOCKED',engine.next_tasks(a,{'prs':{}})['status'])
    def test_native_sandbox_denies_original_credentials_and_external_network(self):
        profile=repair.isolation('/tmp/test-home','/tmp/test-source','/tmp/test-root')
        self.assertIn('(deny network-outbound)',profile)
        self.assertIn('.codex',profile);self.assertIn('.config/gh',profile)
        self.assertIn('(deny file-write*)',profile)
    def test_release_report_cannot_be_claimed_from_model(self):
        with self.assertRaises(ValueError): repair.exact_release({'status':'PASS'},'a'*40)
    def test_repairs_cannot_skip_enrollment(self):
        e=engine.Engine('/tmp',lambda x:None,lambda:False)
        e.analysis={'pr':1,'head':'a'*40,'base':'b'*40,'ci':{'status':'PASS'}}
        e.review={**self.result('CHANGES_REQUIRED'),'files':['src/a.ts'],'tests':['test']}
        with patch.object(engine.follow,'check_identity'),patch.object(engine.follow.Store,'load',return_value=engine.follow.empty_state()):
            with self.assertRaisesRegex(ValueError,'TRUSTED_ENROLLMENT_REQUIRED'):e.repair_preflight()
    def test_cas_lock_and_budget_are_existing_authority(self):
        state=engine.follow.empty_state();state['lock']='other'
        with self.assertRaisesRegex(ValueError,'CONCURRENT_SESSION'):
            engine.follow.reserve_analysis(state,{'pr':1,'head':'a'*40,'ci':{'status':'PASS'}},'local',0)
    def test_browser_has_no_chatgpt_automation_or_persistent_context(self):
        source=(ROOT/'tools/local-controller/launch.mts').read_text()
        self.assertIn('headless: false',source)
        for forbidden in ['storageState(','.cookies(', 'launchPersistentContext(', 'chatgpt.com']:
            self.assertNotIn(forbidden,source)

if __name__=='__main__':unittest.main()

class LocalHTTPTests(unittest.TestCase):
    def test_loopback_token_and_origin_are_required(self):
        import server
        import threading
        import urllib.request
        import urllib.error
        app=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{app.server_port}'
        try:
            with self.assertRaises(urllib.error.HTTPError) as err: urllib.request.urlopen(base+'/state')
            self.assertEqual(403,err.exception.code)
            req=urllib.request.Request(base+'/state',headers={'X-Luma-Token':server.TOKEN})
            self.assertIn('phase',json.load(urllib.request.urlopen(req)))
            req=urllib.request.Request(base+'/merge',data=b'{}',headers={'X-Luma-Token':server.TOKEN,'Origin':'https://evil.example'})
            with self.assertRaises(urllib.error.HTTPError) as err: urllib.request.urlopen(req)
            self.assertEqual(403,err.exception.code)
            req=urllib.request.Request(base+'/state',headers={'X-Luma-Token':server.TOKEN,'Host':'evil.example'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
        finally:app.shutdown();app.server_close();thread.join()

class NativeIsolationTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='darwin','macOS sandbox required')
    def test_real_sandbox_permits_owned_output_but_denies_external_write(self):
        import subprocess,tempfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();temp=root/'temp';temp.mkdir()
            outside=root/'outside';outside.write_text('preserve')
            profile=repair.isolation(temp,source,temp)
            allowed=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,'/bin/sh','-c','echo yes > "$1"','sh',str(source/'test')],capture_output=True)
            denied=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,'/bin/sh','-c','echo no > "$1"','sh',str(outside)],capture_output=True)
            self.assertEqual(0,allowed.returncode,allowed.stderr)
            self.assertNotEqual(0,denied.returncode)
            self.assertEqual('preserve',outside.read_text())
