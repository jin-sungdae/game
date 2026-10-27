import json
import unittest
from test_assets import ROOT
from test_creature_new_pose_quality import measure_parts


class Asset21Tests(unittest.TestCase):
    def test_isolated_candidates_preserve_anatomy_and_registration(self):
        root = ROOT / 'design/production-batches/LUMA-ASSET-21'
        for relative in ('M089/interact', 'M090/cursor_react', 'M087/cursor_react', 'M088/hit', 'M090/interact'):
            with self.subTest(candidate=relative):
                folder = root / relative
                result = measure_parts(folder)
                self.assertEqual(result, json.loads((folder / 'frame-validation.json').read_text()))
                self.assertEqual(result['automated'], 'PASS')
                self.assertEqual(result['uniquePixelHashes'], 8)
                spec = json.loads((folder / 'candidate-clip.json').read_text())
                self.assertFalse(spec['runtimeEnabled'])
                self.assertFalse(spec['productionEligible'])
                self.assertFalse(spec['clip']['loop'])

    def test_eye_ring_layers_reconstruct_original_without_inventing_occlusion(self):
        import hashlib
        from test_moa_blink_v2 import rgba
        folder = ROOT / 'design/production-batches/LUMA-ASSET-21/M087/layers'
        evidence = json.loads((folder / 'layer-validation.json').read_text())
        eye, ring = rgba(folder / 'eye.png'), rgba(folder / 'ring.png')
        base = rgba(ROOT / evidence['source'])
        self.assertTrue(all(a == 0 or b == 0 for a, b in zip(eye[3::4], ring[3::4])))
        self.assertEqual(bytes(a + b for a, b in zip(eye, ring)), base)
        self.assertEqual(hashlib.sha256(base).hexdigest(), evidence['roundtripPixelHash'])
        self.assertFalse(evidence['independentOcclusionReady'])

    def test_generated_gaze_failure_is_preserved_without_cleanup(self):
        import hashlib
        folder = ROOT / 'design/production-batches/LUMA-ASSET-21/M089/look-keypose'
        evidence = json.loads((folder / 'source-validation.json').read_text())
        self.assertEqual(hashlib.sha256((folder / 'source-tool.png').read_bytes()).hexdigest(), evidence['sourceSha256'])
        self.assertEqual(evidence['threshold'], 0)
        self.assertEqual(evidence['detachedAlphaPixels'], 2996)
        self.assertFalse(evidence['normalizationPerformed'])
        self.assertFalse(evidence['riggingPerformed'])
        self.assertFalse((folder / 'rigged').exists())
