import json
import unittest
from test_assets import ROOT

class CreatureReviewTests(unittest.TestCase):
    def test_catalog_preserves_queue_identities_and_does_not_authorize_production(self):
        catalog=json.loads((ROOT/'tests/live/creature-review/catalog.json').read_text())
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        self.assertEqual({r['id'] for r in catalog['creatures']},{r['creatureId'] for r in queue['creatures']})
        self.assertEqual(len(catalog['creatures']),115);self.assertFalse(catalog['productionRegistration'])
        for row in catalog['creatures']:
            if row['id'].startswith('M'):self.assertEqual(row['productionSpeciesId'],'CAPLET' if row['id']=='M005' else None)
            for clip in row['clips']:
                self.assertFalse(clip['runtimeEnabled']);self.assertEqual(clip['artwork'],'HUMAN_REVIEW_REQUIRED')
                self.assertEqual(clip['frameCount'],len(clip['urls']))
                self.assertTrue(all(p.startswith('/design/') and (ROOT/p.lstrip('/')).is_file() for p in clip['urls']))
                self.assertEqual(clip['automated']=='PASS',not clip['errors'])
                if clip['automated']=='PASS':self.assertEqual(len(set(clip['pixelHashes'])),clip['frameCount'])
