import json
import unittest
from test_assets import ROOT, validator
from test_creature_followup import measure, detached_pixels
from test_moa_blink_v2 import rgba

class ContinuationCandidatesTests(unittest.TestCase):
    def test_new_eye_clips_preserve_alpha_and_anatomy(self):
        for code in ('M003','M006','ruu/stage03'):
            folder=ROOT/'design/production-batches/action-followup'/code
            spec=json.loads((folder/'candidate-clip.json').read_text()); eyes=spec['eyes']
            measured=measure(folder,lambda x,y:any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in eyes))
            self.assertEqual(measured,json.loads((folder/'frame-validation.json').read_text()))
            self.assertEqual(measured['automated'],'PASS')
            self.assertEqual(measured['uniquePixelHashes'],spec['clip']['frames'])
            self.assertFalse(spec['productionEligible']);self.assertFalse(spec['runtimeEnabled'])
            self.assertEqual(spec['artworkReview'],'HUMAN_REVIEW_REQUIRED')
        # Numerical loop difference is retained separately from natural motion approval.
        report=json.loads((ROOT/'design/production-batches/action-followup/M003/frame-validation.json').read_text())
        self.assertFalse(report['loopWithinInteriorDeltaRange'])
        self.assertEqual(report['naturalLoop'],'HUMAN_REVIEW_REQUIRED')

    def test_move_turn_keyposes_fail_closed_and_originals_remain(self):
        for action,count in [('move',30),('turn',38)]:
            folder=ROOT/f'design/production-batches/monsters/{action}-pilot/M005'
            report=json.loads((folder/'keypose-validation.json').read_text());bounds=[];hashes=[]
            self.assertTrue((folder/'keypose-tool-reference.png').is_file())
            self.assertEqual(validator.png_errors(folder/'keypose.png',True,bounds,hashes),report['pngErrors'])
            self.assertEqual(bounds,report['bounds']);self.assertEqual(hashes[0],report['pixelHash'])
            self.assertEqual(detached_pixels(rgba(folder/'keypose.png')),count)
            self.assertEqual(report['detachedAlphaPixels'],count)
            self.assertFalse(report['productionEligible']);self.assertFalse(report['animationClipComplete'])
            self.assertFalse((folder/'rigged').exists())

    def test_production_registry_and_repair_limit_are_not_bypassed(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual(queue['repairIterations'],3)
        self.assertEqual(queue['restFollowup']['repairIterations'],3)
        caplet=next(r for r in queue['creatures'] if r['creatureId']=='M005')
        self.assertFalse(caplet['spawn']['enabled'])
        for name in ('MOVE','TURN','INTERACT','REST'):
            action=next(a for a in caplet['actions'] if a['action']==name)
            self.assertEqual(action['animationStatus'],'VALIDATION_FAILED')
            self.assertEqual(action['runtimeStatus'],'BLOCKED')
            self.assertEqual(action['frameCount'],0)
        self.assertEqual(set(json.loads((ROOT/'public/assets/monsters/caplet/manifest.json').read_text())['animations']),{'sleep'})
