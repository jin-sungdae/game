"""Synthetic geometry/unit evidence, never presented as native GUI acceptance."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/gui_qa'))
import environment as e
from common_trace import normalize
from common_analyzer import analyze_trace, nearest


def snapshot():
    return dict(complete=True,screenRecording=True,accessibility=True,screenId=1,
        frame=dict(x=0,y=0,w=1920,h=1080),visibleFrame=dict(x=0,y=0,w=1920,h=1055),
        displays=[],obstacles=[],lumaWindows=[],lumaProcessCount=0,docks=[],cursor=[10,10],
        space={'id':None,'status':'UNAVAILABLE_PUBLIC_API'})
PROFILE=dict(panelSize=[96,104],zone='FREE_AREA',label='TEST',entityId='test',entityType='MONSTER',
    states={'HOVER':{'frames':2,'loop':True,'required':True,'maxSpeed':3}},velocityEpsilon=3)


class EnvironmentTests(unittest.TestCase):
    def test_ready_and_blocked_are_read_only(self):
        s=snapshot();original=copy.deepcopy(s)
        with patch('subprocess.run',side_effect=AssertionError('mutation')):
            self.assertEqual(e.assess(s,PROFILE)['status'],'READY')
            self.assertEqual(s,original)
            s['obstacles']=[{'id':1,'bounds':s['frame']}]
            original=copy.deepcopy(s);r=e.assess(s,PROFILE)
            self.assertEqual(r['status'],e.BLOCKED);self.assertEqual(r['userWindowMutations'],0)
            self.assertEqual(s,original)
    def test_unknown_and_invalid_fail_closed(self):
        for key,value in [('complete',False),('screenRecording',False),('accessibility',False),('cursor',[float('nan'),0]),('screenId',None),('lumaProcessCount',1)]:
            s=snapshot();s[key]=value;self.assertEqual(e.assess(s,PROFILE)['status'],e.BLOCKED,key)
        self.assertEqual(e.assess({},PROFILE)['status'],e.BLOCKED)
    def test_capacity_and_small_screen(self):
        s=snapshot();s['obstacles']=[{'id':n,'bounds':dict(x=-200,y=-200,w=10,h=10)} for n in range(65)]
        self.assertEqual(e.assess(s,PROFILE)['reason'],'METADATA_CAPACITY')
        s=snapshot();s['frame']['w']=400
        self.assertEqual(e.assess(s,PROFILE)['status'],e.BLOCKED)
    def test_dock_cursor_and_negative_origin(self):
        s=snapshot();s['frame']['x']=-1920;s['visibleFrame']['x']=-1920
        self.assertEqual(e.assess(s,PROFILE)['status'],'READY')
        s=snapshot();s['docks']=[dict(x=0,y=0,w=1920,h=300)]
        self.assertEqual(e.assess(s,PROFILE)['status'],'READY')
        s['obstacles']=[{'id':1,'bounds':dict(x=0,y=300,w=1920,h=780)}]
        self.assertEqual(e.assess(s,PROFILE)['status'],e.BLOCKED)
    def test_stability_and_order_independent_fingerprint(self):
        s=snapshot();s['obstacles']=[{'id':1,'bounds':dict(x=-20,y=0,w=10,h=10)},{'id':2,'bounds':dict(x=-40,y=0,w=10,h=10)}]
        t=copy.deepcopy(s);t['obstacles'].reverse();self.assertEqual(e.fingerprint(s),e.fingerprint(t))
        now=[0.0]
        def sleep(n): now[0]+=n
        r=e.gate(lambda:s,PROFILE,clock=lambda:now[0],sleep=sleep)
        self.assertEqual(r['status'],'READY');self.assertGreaterEqual(r['stableSeconds'],3)
        now[0]=0
        def changing():
            t=copy.deepcopy(s);t['screenId']=1 if now[0]<1 else 2;return t
        self.assertEqual(e.gate(changing,PROFILE,clock=lambda:now[0],sleep=sleep)['reason'],'UNSTABLE_GEOMETRY')
    def test_production_contract_guard(self):
        self.assertTrue(e.verify_contract())
        with patch.object(e,'verify_contract',return_value=False),patch.object(e.time,'sleep'),patch.object(e,'observe',side_effect=AssertionError('must not observe')):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                r=e.prepare(None,PROFILE,Path(d)/'report.json',0)
                self.assertEqual(r['reason'],'PRODUCTION_CONTRACT_CHANGED')
    def test_no_window_mutation_capabilities(self):
        source=(ROOT/'scripts/gui_qa/environment_probe.m').read_text()
        for forbidden in ('AXUIElementSetAttributeValue','CGEventPost','activateWithOptions','kCGWindowName'):
            self.assertNotIn(forbidden,source)


class TraceTests(unittest.TestCase):
    def test_missing_telemetry_not_inferred(self):
        row=normalize(dict(before=1,after=1.01,label='TEST HOVER frame 1 animation',panels=[],image={}),PROFILE,snapshot())
        self.assertIsNone(row['vx']);self.assertIsNone(row['nativeFacing']);self.assertIsNone(row['world'])
        self.assertEqual(analyze_trace([row],PROFILE)['facing'],'NOT_VERIFIED')
        self.assertEqual(analyze_trace([row],PROFILE)['frameOrder'],'NOT_VERIFIED')
    def test_order_cycle_facing_and_state(self):
        rows=[]
        for i,frame in enumerate([1,2,1,2,1]):
            r=normalize(dict(before=i*.1,after=i*.1+.001,label=f'TEST HOVER frame {frame} animation trace {{"vx":4,"speed":4,"facing":-1,"rendererFlip":-1}}'),PROFILE,snapshot());rows.append(r)
        result=analyze_trace(rows,PROFILE)
        self.assertEqual(result['frameOrder'],'PASS');self.assertAlmostEqual(result['cycles']['HOVER']['medianMs'],200)
        self.assertEqual(result['facing'],'FAIL');self.assertEqual(result['stateVelocityAgreement'],'FAIL')
        rows[1]['animationFrame']=3;self.assertEqual(analyze_trace(rows,PROFILE)['frameOrder'],'FAIL')
    def test_nearest_has_skew_bound(self):
        rows=[{'timestamp':1},{'timestamp':2}]
        self.assertEqual(nearest(rows,[1,2],1.1,.2),rows[0])
        self.assertIsNone(nearest(rows,[1,2],1.5,.2))
    def test_empty_is_not_pass(self):
        self.assertEqual(analyze_trace([],PROFILE)['frameOrder'],'NOT_VERIFIED')



class CleanupTests(unittest.TestCase):
    def test_pid_reuse_never_kills_user_process(self):
        import tempfile
        import cleanup_environment as cleanup
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'session.json').write_text(json.dumps({'appPid':123,'appPidIdentity':'old owned command'}))
            with patch.object(cleanup,'identity',return_value='different user process'),patch.object(cleanup.os,'kill',side_effect=AssertionError('must not kill')):
                result=cleanup.cleanup(root)
                self.assertEqual(result['status'],'NOT_VERIFIED')
    def test_not_started_cleanup(self):
        import tempfile
        import cleanup_environment as cleanup
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'session.json').write_text('{}')
            self.assertEqual(cleanup.cleanup(root)['status'],'PASS')

class LauncherTests(unittest.TestCase):
    def test_blocked_gate_never_starts_app_or_server(self):
        import tempfile
        import launch_environment as launch
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'run'
            args=['qa','--bundle','/nonexistent.app','--profile',str(ROOT/'scripts/gui_qa/profiles/moa.json'),'--output',str(target)]
            with patch.object(sys,'argv',args),patch.object(launch,'compile_probe'),patch.object(launch,'prepare',return_value={'status':e.BLOCKED}),patch.object(launch.sp,'Popen',side_effect=AssertionError('must not launch')),patch.object(launch.sp,'run',side_effect=AssertionError('must not run')):
                self.assertEqual(launch.main(),2)
                self.assertFalse((target/'session').exists())
    def test_only_own_pid_is_cleaned_up(self):
        import cleanup_environment as cleanup
        import tempfile,subprocess
        child=subprocess.Popen([sys.executable,'-c','import time; print("ready",flush=True); time.sleep(30)'],stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'ready')
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'session.json').write_text(json.dumps({'appPid':child.pid,'appPidIdentity':cleanup.identity(child.pid)}))
                result=cleanup.cleanup(root)
                self.assertEqual(result['status'],'PASS')
                child.wait(timeout=3)
        finally:
            if child.poll() is None: child.terminate();child.wait()
            child.stdout.close()


class PixelTests(unittest.TestCase):
    def test_panel_local_drift_and_clipping_with_moving_world(self):
        try: from PIL import Image,ImageDraw
        except ImportError: self.skipTest('Pillow optional QA pixel dependency')
        import tempfile
        from common_analyzer import measure
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);frames=[];rows=[]
            for i in range(3):
                image=Image.new('RGBA',(192,208));draw=ImageDraw.Draw(image);draw.rectangle((50,80,100,180),fill='white');image.save(root/f'{i}.png')
                frames.append(dict(file=f'{i}.png',wallTime=i,width=192,height=208))
                rows.append(dict(timestamp=i,animationState='HOVER',animationFrame=1,rendererFlip=1,panelBounds=dict(x=100+i*20,y=100,w=96,h=104),canvasBounds=dict(x=100+i*20,y=100,w=96,h=104)))
            (root/'frames.json').write_text(json.dumps({'frames':frames}))
            p=dict(PROFILE,maxTraceSkewSeconds=.05,pixelMask={'method':'alpha','threshold':0},sourceBounds=[10,20,240,250],sourceCanvas=[256,256])
            r=measure(root,rows,p)
            self.assertEqual(r['matchedFrames'],3)
            self.assertEqual(r['driftPtByStateFacing'][0]['centerX'],0)
            self.assertEqual(r['driftPtByStateFacing'][0]['bottom'],0)
            self.assertEqual(r['clipping'],'NO_MASK_EDGE_CONTACT')
            self.assertEqual(r['mirrorOffset'],'NOT_VERIFIED')
            image=Image.open(root/'0.png');ImageDraw.Draw(image).rectangle((0,0,191,207),fill='white');image.save(root/'0.png')
            self.assertEqual(measure(root,rows,p)['clipping'],'EDGE_CONTACT_REVIEW_REQUIRED')


if __name__=='__main__': unittest.main()
