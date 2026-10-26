import json
import unittest
from pathlib import Path

class CreatureQueueTests(unittest.TestCase):
    def test_queue_is_complete_and_never_aliases_concept_ids(self):
        data=json.loads((Path(__file__).resolve().parents[2]/'design/creature-production-queue.json').read_text())
        rows=data['creatures'];ids={r['creatureId'] for r in rows}
        self.assertEqual(len(rows),115)
        self.assertEqual(ids,{f'companion:{s}:{n}' for s in ['moa','ruu','nox'] for n in range(1,6)}|{f'M{n:03}' for n in range(1,101)})
        for row in rows:
            self.assertIn('lastValidatedCommit',row)
            self.assertEqual(len({a['action'] for a in row['actions']}),len(row['actions']))
            if row['creatureId'].startswith('M'):
                self.assertEqual(row['productionSpeciesId'], 'CAPLET' if row['creatureId']=='M005' else None)
                self.assertEqual(bool(row.get('identityMappingApproved')), row['creatureId']=='M005')
                self.assertEqual(row['runtimeStatus'],'PARTIAL_PRESENTATION_CONNECTED' if row['creatureId']=='M005' else 'BLOCKED')
            if row['state']=='PRODUCTION_READY':
                self.assertEqual(row['guiStatus'],'PASS')
                self.assertTrue(all(a['animationStatus']=='ANIMATION_READY' and a['guiStatus']=='PASS' for a in row['actions']))
        self.assertFalse(data['fullProductionReady'])
