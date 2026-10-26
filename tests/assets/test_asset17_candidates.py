"""Session-scoped candidate regression; never promotes assets or shared ledgers."""
import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts

BATCH = ROOT / 'design/production-batches/LUMA-ASSET-17'


def measure(folder):
    result = measure_parts(folder)
    spec = json.loads((folder / 'candidate-clip.json').read_text())
    deltas = result['adjacentPixelDifferenceSumsIncludingLoop']
    result['loopContract'] = 'CANDIDATE_LOOP' if spec['clip']['loop'] else 'ONE_SHOT'
    result['loopBoundaryWithinAdjacentMaximum'] = deltas[-1] <= max(deltas[:-1])
    if spec['clip']['loop'] and not result['loopBoundaryWithinAdjacentMaximum']:
        result['automated'] = 'VALIDATION_FAILED'
    return result


class Asset17Candidates(unittest.TestCase):
    def test_candidate_geometry_continuity_and_isolation(self):
        folders = sorted(BATCH.glob('M*/*/candidate-clip.json'))
        self.assertEqual(len(folders), 6)
        hashes = set()
        for file in folders:
            with self.subTest(clip=str(file)):
                spec = json.loads(file.read_text())
                result = measure(file.parent)
                self.assertEqual(result, json.loads((file.parent/'frame-validation.json').read_text()))
                expected = 'VALIDATION_FAILED' if file.parent.parent.name == 'M070' and file.parent.name == 'cursor_react' else 'PASS'
                self.assertEqual(result['automated'], expected)
                if expected == 'VALIDATION_FAILED':
                    self.assertEqual(sum('DETACHED_ALPHA' in frame['errors'] for frame in result['frames']), 2)
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                for frame in result['frames']:
                    self.assertNotIn(frame['pixelHash'], hashes)
                    hashes.add(frame['pixelHash'])
                rig = json.loads((file.parent/'rig-evidence.json').read_text())
                self.assertEqual(rig['repairIterations'], 3)
                self.assertFalse(rig['wholeImageTransform'])
                self.assertTrue(all(f['fixedRegionChanges'] == 0 for f in rig['frames']))
