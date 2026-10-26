"""Narrow delivery regression: actual decoded hashes, protected anatomy and approval boundaries."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

class DeliveryTests(unittest.TestCase):
    def test_measured_frames_match_current_pixels_and_protected_anatomy(self):
        count=0
        for p in OUT.glob('M*/*/frame-validation.json'):
            report=json.loads(p.read_text());spec=json.loads(p.with_name('candidate-clip.json').read_text())
            if report['automated']!='PASS':continue
            base=Image.open(ROOT/spec['sourceBase']);base_pixels=base.tobytes();hashes=set()
            for row in report['frames']:
                path=p.parent/'rigged'/spec['clip']['name'].lower()/row['file']
                im=Image.open(path);pixels=im.tobytes()
                self.assertEqual((im.size,im.mode),((256,256),'RGBA'))
                self.assertEqual(hashlib.sha256(pixels).hexdigest(),row['pixelHash'])
                hashes.add(row['pixelHash']);self.assertEqual(row['errors'],[])
                self.assertEqual(row['anchorDriftPixels'],{'bottom':0,'boundsCenterX':0})
                for y in range(256):
                    for x in range(256):
                        if 'eyes' in spec:
                            movable=any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in spec['eyes'])
                        else:
                            l,t,r,b=spec['movableRect'];movable=l<x<r and t<y<b
                        if not movable:
                            n=(y*256+x)*4
                            self.assertEqual(pixels[n:n+4],base_pixels[n:n+4])
            self.assertEqual(len(hashes),spec['clip']['frames']);count+=1
        self.assertEqual(count,12)

    def test_candidates_never_claim_production_or_reset_repair_budget(self):
        for p in OUT.glob('M*/*/candidate-clip.json'):
            spec=json.loads(p.read_text())
            self.assertFalse(spec['productionEligible']);self.assertFalse(spec['runtimeEnabled'])
            self.assertEqual((spec['repairIterations'],spec['repairLimit']),(3,3))
        request=json.loads((OUT/'integration-request.json').read_text())
        for monster in request['monsters']:
            self.assertEqual(len(monster['actions']),21)
            self.assertIsNone(monster['productionSpeciesId'])

    def test_failed_sources_remain_unmodified(self):
        for p in OUT.glob('M*/*/source-validation.json'):
            r=json.loads(p.read_text());source=p.with_name('source-keypose.png')
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),r['sourceSha256'])
            self.assertEqual(r['status'],'BLOCKED');self.assertGreater(r['detachedAlphaPixels'],0)
            self.assertFalse(r['failureRecoveryAttempted'])
            self.assertFalse((p.parent/'rigged').exists())

if __name__=='__main__':unittest.main()
