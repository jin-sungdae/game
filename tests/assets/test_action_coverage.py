import json
import sys
import tempfile
import unittest
from pathlib import Path
from test_assets import ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from build_creature_review import coverage, manifest_supply

class ActionCoverageTests(unittest.TestCase):
    def test_ready_claim_without_frames_or_gui_is_not_completion(self):
        action={'action':'IDLE','animationStatus':'ANIMATION_READY','runtimeStatus':'RUNTIME_CONNECTED','guiStatus':'GUI_NOT_VERIFIED'}
        result=coverage([action],[],{})
        self.assertEqual(result['recordedRuntimeActions'],1)
        self.assertEqual(result['manifestFileSetsPresent'],0)
        self.assertEqual(result['completeActions'],0)
        self.assertEqual(result['missingFrameSetActions'],1)
        action['guiStatus']='PASS'
        self.assertEqual(coverage([action],[],{'idle':{'completeFileSet':True}})['completeActions'],1)

    def test_candidate_versions_never_double_count_actions_or_approve_them(self):
        action={'action':'BLINK','animationStatus':'VALIDATION_FAILED','runtimeStatus':'BLOCKED','guiStatus':'GUI_NOT_VERIFIED'}
        clips=[{'action':'blink','automated':'PASS'},{'action':'blink','automated':'VALIDATION_FAILED'}]
        result=coverage([action],clips,{})
        self.assertEqual(result['candidateActions'],1)
        self.assertEqual(result['automatedCandidateActions'],1)
        self.assertEqual(result['validationFailedActions'],1)
        self.assertEqual(result['artworkReviewPendingActions'],1)
        self.assertEqual(result['completeActions'],0)

    def test_declared_missing_frames_and_filename_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'edge_move').mkdir()
            (root/'edge_move/edge_01.png').touch()
            path=root/'manifest.json'
            path.write_text(json.dumps({'animations':{'edge_move':{'frames':2,'firstFrame':1,'filePrefix':'edge'},'look':{'frames':4}}}))
            supply=manifest_supply(path)
            self.assertEqual(supply['edge_move']['presentFrames'],1)
            self.assertFalse(supply['edge_move']['completeFileSet'])
            self.assertEqual(supply['look']['presentFrames'],0)
            (root/'edge_move/edge_02.png').touch()
            self.assertTrue(manifest_supply(path)['edge_move']['completeFileSet'])

    def test_ledger_catalog_and_legacy_identity_scopes_match(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        catalog=json.loads((ROOT/'tests/live/creature-review/catalog.json').read_text())
        by_id={r['id']:r for r in catalog['creatures']}
        self.assertEqual(len(by_id),115)
        for row in queue['creatures']:
            self.assertEqual(row['animationCoverage'],by_id[row['creatureId']]['coverage'])
            self.assertEqual(row['animationCoverage'],coverage(row['actions'],by_id[row['creatureId']]['clips'],by_id[row['creatureId']]['manifestSupply']))
        total=catalog['coverageSummary']
        self.assertEqual(queue['animationCoverageSummary'],total)
        self.assertEqual(total['requiredActions'],1740)
        self.assertEqual(total['completeCreatures'],0)
        self.assertEqual(len(catalog['legacyProductionAudit']),30)
        self.assertTrue(all(r['conceptMapping']=='NOT_ASSUMED' for r in catalog['legacyProductionAudit']))
        self.assertEqual(queue['legacyProductionAudit'],catalog['legacyProductionAudit'])
