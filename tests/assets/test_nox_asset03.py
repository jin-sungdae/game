import hashlib
import json
import unittest
from pathlib import Path
from test_assets import ROOT, validator
from test_moa_blink_v2 import rgba
from test_creature_followup import detached_pixels

BATCH = ROOT / "design/production-batches/LUMA-ASSET-03/nox/stage02"
ACTIONS = ("breath", "skill_cast", "victory")

def measure(folder):
    spec = json.loads((folder / "candidate-clip.json").read_text())
    base_path = ROOT / spec["sourceBase"]
    base = rgba(base_path)
    base_bounds = []
    base_errors = validator.png_errors(base_path, True, base_bounds)
    left, top, right, bottom = spec["movableRect"]
    action = spec["clip"]["name"].lower()
    frames = []
    decoded = []
    hashes = []
    for index, path in enumerate(sorted((folder / "rigged" / action).glob("*.png"))):
        bounds = []
        errors = validator.png_errors(path, True, bounds, hashes)
        pixels = rgba(path)
        decoded.append(pixels)
        protected = changed = 0
        for i in range(0, len(pixels), 4):
            if pixels[i:i+4] != base[i:i+4]:
                changed += 1
                x, y = (i//4)%256, (i//4)//256
                if not (left < x < right and top < y < bottom):
                    protected += 1
        detached = detached_pixels(pixels)
        edge = sum(pixels[(y*256+x)*4+3]>0 for y in range(256) for x in range(256)
                   if x in (0,255) or y in (0,255))
        alpha_changed = sum(a!=b for a,b in zip(pixels[3::4],base[3::4]))
        drift = sum(abs(a-b) for a,b in zip(pixels,base))/len(base)/255
        if path.name != f"{action}_{index:02}.png": errors.append("NONCANONICAL_SEQUENCE")
        if bounds != base_bounds: errors.append("BOUNDS_DRIFT")
        if protected: errors.append("PROTECTED_ANATOMY_CHANGED")
        if detached: errors.append("DETACHED_ALPHA")
        if edge: errors.append("CANVAS_EDGE_CLIPPING")
        if not alpha_changed: errors.append("NO_LOCAL_SILHOUETTE_MOTION")
        if drift > .006: errors.append("EXCESSIVE_MEASURED_APPEARANCE_DRIFT")
        frames.append(dict(file=path.name,errors=errors,bounds=bounds,
            pixelHash=hashlib.sha256(pixels).hexdigest(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            protectedPixelChanges=protected,changedPixels=changed,alphaChangedPixels=alpha_changed,
            detachedAlphaPixels=detached,canvasEdgePixels=edge,normalizedRgbaDifferenceFromBase=drift,
            anchorDriftPixels=dict(bottom=bounds[3]-base_bounds[3],
                                  boundsCenterX=(bounds[0]+bounds[2]-base_bounds[0]-base_bounds[2])/2)))
    differences = [sum(abs(a-b) for a,b in zip(decoded[i],decoded[(i+1)%len(decoded)]))/len(base)/255
                   for i in range(len(decoded))]
    errors = list(base_errors)
    if detached_pixels(base): errors.append("SOURCE_ALPHA_DEFECT")
    if len(frames)!=8 or len(set(hashes))!=8: errors.append("FRAME_COUNT_OR_DUPLICATE")
    if any(f["errors"] for f in frames): errors.append("FRAME_VALIDATION_FAILED")
    if not all(0<d<.004 for d in differences): errors.append("FRAME_CONTINUITY_BOUND")
    # Return to BASE is measured for one-shots; it is not inferred from preview looping.
    endpoint = sum(abs(a-b) for a,b in zip(decoded[-1],base))/len(base)/255
    if endpoint > .001: errors.append("ENDPOINT_DISCONTINUITY")
    return dict(automated="PASS" if not errors else "VALIDATION_FAILED",errors=errors,
        sourceSha256=hashlib.sha256(base_path.read_bytes()).hexdigest(),frames=frames,
        uniquePixelHashes=len(set(hashes)),adjacentNormalizedRgbaDifferenceIncludingWrap=differences,
        endpointDifferenceFromBase=endpoint,
        continuityScope="Numerical RGBA change only; anatomy and natural motion require human review",
        appearance="HUMAN_REVIEW_REQUIRED",naturalMotion="HUMAN_REVIEW_REQUIRED",
        nativeGui="DEFERRED_GUI",productionEligible=False)

class NoxAsset03Tests(unittest.TestCase):
    def test_candidate_metrics_match_existing_decoder_and_safe_regions(self):
        all_hashes=set()
        for action in ACTIONS:
            with self.subTest(action=action):
                folder=BATCH/(action+"-pilot")
                result=measure(folder)
                self.assertEqual(result,json.loads((folder/"frame-validation.json").read_text()))
                self.assertEqual(result["automated"],"PASS",result["errors"])
                self.assertEqual(result["uniquePixelHashes"],8)
                all_hashes.update(f["pixelHash"] for f in result["frames"])
                spec=json.loads((folder/"candidate-clip.json").read_text())
                self.assertFalse(spec["runtimeEnabled"])
                self.assertFalse(spec["productionEligible"])
                self.assertEqual(spec["clip"]["loop"],action=="breath")
                self.assertEqual(spec["anchor"],{"x":.5,"y":1})
        self.assertEqual(len(all_hashes),24)

    def test_prior_failures_ledger_and_production_are_unchanged(self):
        evidence=json.loads((BATCH.parent.parent/"preservation.json").read_text())
        for path,digest in evidence["protectedFiles"].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
        self.assertEqual(evidence["priorRepairIterations"],3)
        self.assertEqual(evidence["sessionId"],"LUMA-ASSET-03")
        queue=json.loads((ROOT/"design/creature-production-queue.json").read_text())
        for stage in (1,3,4,5):
            row=next(r for r in queue["creatures"] if r["creatureId"]==f"companion:nox:{stage}")
            self.assertEqual(row["state"],"BLOCKED")

    def test_existing_review_catalog_discovers_candidates_without_ledger_edit(self):
        import sys
        sys.path.insert(0,str(ROOT/"scripts"))
        import build_creature_review as review
        # Inspect only our isolated design subtree while keeping canonical registry inputs.
        from unittest.mock import patch
        original=Path.glob
        def local_glob(path,pattern):
            if path==ROOT/"design" and pattern=="**/rigged/*":
                return original(BATCH,pattern)
            return original(path,pattern)
        with patch.object(Path,"glob",local_glob):
            catalog=review.build()
        row=next(r for r in catalog["creatures"] if r["id"]=="companion:nox:2")
        self.assertEqual({c["action"] for c in row["clips"]},set(ACTIONS))
        self.assertTrue(all(c["automated"]=="PASS" for c in row["clips"]))
        self.assertTrue(all(not c["runtimeEnabled"] for c in row["clips"]))
