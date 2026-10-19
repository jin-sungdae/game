import json
import tempfile
import unittest
from pathlib import Path
import sys
from test_assets import ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from build_creature_review import inventory_counts

class ReviewInventoryTests(unittest.TestCase):
    def test_counts_keep_candidate_source_review_and_production_scopes_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for relative in ['design/production-batches/monsters/M001/source-v1.png','design/production-batches/monsters/M001/base-v2.png','design/production-batches/monsters/M001/rigged/idle/idle_00.png','design/production-batches/breath-followup/M001/rigged/breath/breath_00.png','public/assets/monsters/pip/base.png']:
                p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
            self.assertEqual(inventory_counts(root),{'allCandidatePng':3,'sourcePngIncludingRecovery':1})
    def test_actual_ledger_matches_measured_inventory(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        for key,value in inventory_counts().items():self.assertEqual(queue['candidateInventory'][key],value)
