import hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/'design/production-batches/luma-asset-06'
spec=importlib.util.spec_from_file_location('asset06',BATCH/'validate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Asset06Tests(unittest.TestCase):
    def test_recomputed_measurements_preserve_pass_and_failure(self):
        passed=failed=frames=0
        for folder in sorted(BATCH.glob('M*/*')):
            with self.subTest(candidate=str(folder)):
                measured=module.audit(folder)
                self.assertEqual(measured,json.loads((folder/'frame-validation.json').read_text()))
                passed+=measured['automated']=='PASS';failed+=measured['automated']!='PASS';frames+=len(measured['frames'])
                self.assertFalse(measured['productionEligible']);self.assertEqual(measured['repairIterations'],3)
        self.assertEqual((passed,failed,frames),(15,6,144))

    def test_no_duplicate_existing_actions_or_approval(self):
        queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
        rows={r['creatureId']:r for r in queue['creatures']}
        for path in BATCH.glob('M*/*/candidate-clip.json'):
            candidate=json.loads(path.read_text());row=rows[candidate['conceptId']]
            old=next(a for a in row['actions'] if a['action']==candidate['clip']['name'])
            self.assertEqual(old['animationStatus'],'ASSET_REQUIRED')
            self.assertFalse(candidate['productionEligible']);self.assertFalse(candidate['runtimeEnabled'])
            self.assertEqual(candidate['repairLimit'],candidate['repairIterations'])
            self.assertIsNone(candidate['species'])
        for ident,action in [('M011','REST'),('M012','MOVE')]:
            self.assertEqual(next(a for a in rows[ident]['actions'] if a['action']==action)['animationStatus'],'VALIDATION_FAILED')

    def test_catalog_cannot_promote_continuity_failures(self):
        catalog=json.loads((BATCH/'catalog.json').read_text())
        clips=[c for row in catalog['creatures'] for c in row['clips']]
        self.assertEqual(len(clips),18)
        self.assertEqual(sum(c['automated']=='PASS' for c in clips),15)
        self.assertTrue(all(not c['runtimeEnabled'] for c in clips))

    def test_original_candidates_are_byte_preserved(self):
        digest=hashlib.sha256()
        files=sorted(p for p in BATCH.glob('M*/*/**/*') if p.is_file() and p.relative_to(BATCH).parts[1] not in ['blink','look'])
        for path in files:
            digest.update(str(path.relative_to(BATCH)).encode());digest.update(path.read_bytes())
        self.assertEqual(digest.hexdigest(),"51158a4febce650db0fb18c65b56282f2eaf6069fef559a8dab109a712801656")

    def test_eye_rigs_preserve_alpha_and_non_eye_anatomy(self):
        for action in ['blink','look']:
            for folder in sorted(BATCH.glob('M*/'+action)):
                spec=json.loads((folder/'candidate-clip.json').read_text())
                base=module.rgba(ROOT/spec['sourceBase'])
                for path in sorted((folder/'rigged'/action).glob('*.png')):
                    data=module.rgba(path)
                    self.assertEqual(data[3::4],base[3::4],str(path))
                    changed=0
                    for n in range(0,len(base),4):
                        if data[n:n+4]==base[n:n+4]:continue
                        changed+=1;x=(n//4)%256;y=(n//4)//256
                        self.assertTrue(any(((x-e['x'])/e['rx'])**2+((y-e['y'])/e['ry'])**2<1 for e in spec['parts']),str(path))
                    # BASE endpoints may round to the unchanged source; interior poses must move.
                    if path.stem[-2:] not in ['00','07']:
                        self.assertGreater(changed,0,str(path))
