import json
import unittest
from test_assets import ROOT
from test_creature_followup import measure, detached_pixels
from test_moa_blink_v2 import rgba

class ActionDiversityTests(unittest.TestCase):
    def test_successful_clips_keep_anatomy_alpha_and_unique_frames(self):
        for code in ('M001', 'M002'):
            folder=ROOT/'design/production-batches/action-followup'/code
            spec=json.loads((folder/'candidate-clip.json').read_text()); eyes=spec['eyes']
            report=measure(folder, lambda x,y:any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in eyes))
            self.assertEqual(report,json.loads((folder/'frame-validation.json').read_text()))
            self.assertEqual(report['automated'],'PASS')
            self.assertTrue(report['loopWithinInteriorDeltaRange'])
            self.assertFalse(spec['productionEligible']);self.assertFalse(spec['runtimeEnabled'])
            self.assertEqual(spec['artworkReview'],'HUMAN_REVIEW_REQUIRED')

    def test_failed_blink_is_retained_and_cannot_count_as_pass(self):
        folder=ROOT/'design/production-batches/action-followup/moa/stage04'
        spec=json.loads((folder/'candidate-clip.json').read_text()); eyes=spec['eyes']
        report=measure(folder,lambda x,y:any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in eyes))
        self.assertEqual(report,json.loads((folder/'frame-validation.json').read_text()))
        self.assertEqual((report['automated'],report['uniquePixelHashes']),('VALIDATION_FAILED',5))
        self.assertEqual(len(report['frames']),6)
        self.assertFalse(spec['productionEligible'])

    def test_failed_interact_and_existing_sleep_remain_separate(self):
        folder=ROOT/'design/production-batches/monsters/interact-pilot/M005'
        self.assertTrue((folder/'keypose-tool-reference.png').is_file())
        report=json.loads((folder/'keypose-validation.json').read_text())
        self.assertEqual(detached_pixels(rgba(folder/'keypose.png')),21)
        self.assertEqual(report['detachedAlphaPixels'],21)
        self.assertFalse(report['productionEligible'])
        self.assertFalse((folder/'rigged').exists())
        manifest=json.loads((ROOT/'public/assets/monsters/caplet/manifest.json').read_text())
        self.assertEqual(set(manifest['animations']),{'sleep'})
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual(queue['repairIterations'],3)
        self.assertEqual(queue['restFollowup']['repairIterations'],3)
        caplet=next(r for r in queue['creatures'] if r['creatureId']=='M005')
        self.assertFalse(caplet['spawn']['enabled'])
        self.assertEqual(next(a for a in caplet['actions'] if a['action']=='INTERACT')['animationStatus'],'VALIDATION_FAILED')
