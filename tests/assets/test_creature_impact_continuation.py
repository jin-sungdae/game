import hashlib
import json
import unittest
from pathlib import Path
from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels

BATCH=ROOT/'design/production-batches/action-followup'
CASES={"M013":"M013/hit-pilot","M014":"M014/hit-pilot","companion:ruu:3":"ruu/stage03/hit-pilot","companion:nox:2":"nox/stage02/hit-pilot"}
FAILED={"M012/move-pilot":206,"moa/stage05/rest-pilot":91,"M016/attack-pilot":132}

def measure_impact(folder):
    spec=json.loads((folder/'candidate-clip.json').read_text())
    base=rgba(ROOT/spec['sourceBase']); bb=[]; base_errors=validator.png_errors(ROOT/spec['sourceBase'],True,bb)
    l,t,r,b=spec['movableRect']
    paths=sorted((folder/'rigged/hit').glob('*.png'))
    frames=[]; decoded=[]; hashes=[]
    for n,p in enumerate(paths):
        bounds=[];errors=validator.png_errors(p,True,bounds,hashes);data=rgba(p);decoded.append(data)
        protected=sum(data[i:i+4]!=base[i:i+4] for i in range(0,len(data),4) if not (l<(i//4)%256<r and t<(i//4)//256<b))
        alpha_changes=sum(a!=z for a,z in zip(data[3::4],base[3::4]))
        detached=detached_pixels(data)
        edge=sum(data[(y*256+x)*4+3]>0 for y in range(256) for x in range(256) if x in (0,255) or y in (0,255))
        if p.name!=f'hit_{n:02}.png': errors.append('NONCANONICAL_SEQUENCE')
        if bounds!=bb: errors.append('BOUNDS_DRIFT')
        if protected: errors.append('PROTECTED_ANATOMY_CHANGED')
        if not alpha_changes: errors.append('NO_SILHOUETTE_MOTION')
        if detached: errors.append('DETACHED_ALPHA')
        if edge: errors.append('CANVAS_EDGE_CLIPPING')
        frames.append({'file':p.name,'errors':errors,'bounds':bounds,'pixelHash':hashlib.sha256(data).hexdigest(),'protectedPixelChanges':protected,'alphaChangedPixels':alpha_changes,'detachedAlphaPixels':detached,'canvasEdgePixels':edge,'anchorDriftPixels':{'bottom':bounds[3]-bb[3],'boundsCenterX':(bounds[0]+bounds[2]-bb[0]-bb[2])/2}})
    deltas=[sum(abs(a-b) for a,b in zip(decoded[n],decoded[(n+1)%len(decoded)])) for n in range(len(decoded))]
    passed=not base_errors and detached_pixels(base)==0 and len(paths)==spec['clip']['frames'] and len(set(hashes))==len(paths) and all(deltas) and all(not f['errors'] for f in frames)
    return {'automated':'PASS' if passed else 'VALIDATION_FAILED','frames':frames,'sourceSha256':hashlib.sha256((ROOT/spec['sourceBase']).read_bytes()).hexdigest(),'baseErrors':base_errors,'uniquePixelHashes':len(set(hashes)),'adjacentPixelDifferenceSumsIncludingLoop':deltas,'loopBoundaryDelta':deltas[-1] if deltas else None,'loopContract':'ONE_SHOT: preview repetition is not an approved seamless loop','automatedScope':'Existing PNG validator, RGBA transparency, actual local silhouette change, fixed protected anatomy, bounds, anchor, detached alpha, canvas edge, pixel uniqueness; not artwork or anatomical motion approval','appearance':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','nativeGui':'DEFERRED_GUI','productionEligible':False}


class CreatureImpactContinuationTests(unittest.TestCase):
    def test_four_distinct_impact_clips_move_silhouette_but_keep_face_feet_and_anchor(self):
        signatures=set();durations=set()
        for identity,code in CASES.items():
            with self.subTest(identity=identity):
                folder=BATCH/code;spec=json.loads((folder/'candidate-clip.json').read_text())
                result=measure_impact(folder)
                self.assertEqual(result,json.loads((folder/'frame-validation.json').read_text()))
                self.assertEqual(result['automated'],'PASS')
                self.assertEqual(result['uniquePixelHashes'],8)
                self.assertEqual(len(result['frames']),8)
                self.assertTrue(all(result['adjacentPixelDifferenceSumsIncludingLoop']))
                for frame in result['frames']:
                    self.assertEqual(frame['errors'],[])
                    self.assertGreater(frame['alphaChangedPixels'],0)
                    self.assertEqual(frame['protectedPixelChanges'],0)
                    self.assertEqual(frame['detachedAlphaPixels'],0)
                    self.assertEqual(frame['canvasEdgePixels'],0)
                    self.assertEqual(frame['anchorDriftPixels'],{'bottom':0,'boundsCenterX':0})
                rig=json.loads((folder/'rig-evidence.json').read_text())
                self.assertFalse(rig['wholeImageTransform'])
                self.assertTrue(rig['silhouetteMotion'])
                self.assertTrue(all(0<f['maxInverseDisplacementPixels']<4 for f in rig['frames']))
                self.assertFalse(spec['clip']['loop'])
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertEqual(spec['anchor'],{'x':.5,'y':1})
                signatures.add(json.dumps(spec['parts'],sort_keys=True))
                durations.add(spec['clip']['frameDuration'])
        self.assertEqual(len(signatures),4)
        self.assertEqual(len(durations),4)

    def test_failed_flight_rest_attack_poses_stay_unrepaired_and_unanimated(self):
        for code,detached in FAILED.items():
            with self.subTest(code=code):
                folder=BATCH/code;report=json.loads((folder/'keypose-validation.json').read_text())
                bounds=[];hashes=[]
                self.assertEqual(validator.png_errors(folder/'keypose.png',True,bounds,hashes),report['pngErrors'])
                self.assertEqual(bounds,report['bounds'])
                self.assertEqual(hashes[0],report['pixelHash'])
                self.assertEqual(detached_pixels(rgba(folder/'keypose.png')),detached)
                self.assertEqual(report['detachedAlphaPixels'],detached)
                self.assertEqual(report['status'],'VALIDATION_FAILED')
                self.assertFalse(report['productionEligible'])
                self.assertFalse(report['animationClipComplete'])
                self.assertTrue((folder/'keypose-tool-reference.png').is_file())
                self.assertFalse((folder/'rigged').exists())

    def test_ledger_keeps_approval_runtime_and_repair_boundaries(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        run=queue['impactContinuation']
        self.assertEqual(queue['repairIterations'],3)
        self.assertEqual(run['repairIterations'],3)
        self.assertEqual(run['newCases'],CASES)
        self.assertEqual(run['candidateFrames'],32)
        self.assertEqual(run['candidatePng'],42)
        self.assertEqual(run['productionRegistrations'],0)
        self.assertEqual(run['runtimeConnections'],0)
        self.assertEqual(run['approvedUnconnectedAssets'],[])
        self.assertEqual(sum(len(list((BATCH/code).rglob('*.png'))) for code in [*CASES.values(),*FAILED]),42)
        for identity,code in CASES.items():
            row=next(r for r in queue['creatures'] if r['creatureId']==identity)
            action=next(a for a in row['actions'] if a['action']=='HIT')
            self.assertEqual(action['runtimeStatus'],'BLOCKED')
            self.assertEqual(action['artworkReview'],'HUMAN_REVIEW_REQUIRED')
            self.assertEqual(action['candidatePath'],str((BATCH/code).relative_to(ROOT)))
        for identity,action in [('M012','MOVE'),('companion:moa:5','REST'),('M016','ATTACK')]:
            item=next(a for r in queue['creatures'] if r['creatureId']==identity for a in r['actions'] if a['action']==action)
            self.assertEqual(item['animationStatus'],'VALIDATION_FAILED')
            self.assertEqual(item['frameCount'],0)
        self.assertFalse(next(r for r in queue['creatures'] if r['creatureId']=='M005')['spawn']['enabled'])
        self.assertTrue(run['nextTask'])
