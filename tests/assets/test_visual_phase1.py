"""Independent delivery-contract tests; synthetic data never enters public assets."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import visual_phase1 as phase


class VisualPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = phase.inventory(ROOT)
        cls.catalog = phase.reference_catalog(ROOT)

    def test_fifteen_forms_and_one_hundred_concepts_are_separate_from_existing_monsters(self):
        rows = self.report['characters']
        self.assertEqual(len(rows), 115)
        self.assertEqual(len({r['key'] for r in rows}), 115)
        concepts = [r for r in rows if r['key'].startswith('concept:')]
        self.assertEqual(len(concepts), 100)
        self.assertTrue(all(r['assetRoot'] is None and not r['runtimeRegistered'] for r in concepts))
        existing = self.report['existingMonsterInventory']
        self.assertEqual(len(existing), len(json.loads((ROOT/'src/entities/monster-dex.json').read_text())))
        self.assertTrue(all(not r['key'].startswith('concept:') for r in existing))

    def test_no_full_production_or_behavior_claim(self):
        self.assertEqual(self.report['status'], 'PREPARATION_ONLY')
        self.assertFalse(self.report['runtimeActivation'])
        self.assertEqual(self.report['errors'], [])
        self.assertEqual(self.report['summary']['unassignedMonsterIdentities'], 100)
        for row in self.report['characters']:
            self.assertEqual(set(row['actions']), set(phase.ACTIONS))
            for action in row['actions'].values():
                self.assertEqual(action['binding'], 'REVIEW_REQUIRED')
                self.assertEqual(action['visualApproval'], 'NOT_VERIFIED')
        for row in self.report['characters'][15:]:
            self.assertTrue(all(v['status']=='ASSET_REQUIRED' for v in row['actions'].values()))

    def test_existing_names_and_runtime_paths_are_preserved(self):
        rows = {r['key']:r for r in self.report['characters']}
        self.assertEqual(rows['companion:moa:2']['name'], 'MOKORI')
        self.assertEqual(rows['companion:moa:3']['name'], 'NEBLA')
        self.assertEqual(rows['companion:moa:2']['conceptDesign']['conceptStageLabel'], 'LEAFOR')
        self.assertIsNone(rows['companion:moa:2']['conceptDesign']['productionNameOverride'])
        self.assertFalse(rows['companion:moa:5']['runtimeRegistered'])
        self.assertEqual(rows['companion:ruu:1']['baseStatus'], 'ASSET_REQUIRED')
        self.assertEqual(rows['companion:nox:1']['baseStatus'], 'ASSET_REQUIRED')

    def test_concepts_are_original_whole_sheets_not_frames(self):
        for reference in self.catalog['references'].values():
            data = (ROOT/reference['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), reference['sha256'])
            self.assertEqual(reference['kind'], 'CONCEPT_REFERENCE')
            self.assertFalse(reference['productionEligible'])
            self.assertFalse(reference['path'].startswith('public/'))
        self.assertTrue(all(r['existingMonsterCode'] is None for r in self.catalog['monsterConcepts']))

    def test_runtime_parser_reused_and_malformed_manifest_rejected(self):
        good = json.loads((ROOT/'public/assets/creatures/moa/stage01/manifest.json').read_text())
        requests = []
        for mutate in ('none', 'species', 'anchor', 'prefix', 'duration', 'first', 'count'):
            m = copy.deepcopy(good)
            if mutate=='species': m['species']='ruu'
            if mutate=='anchor': m['anchor']['y']=0
            if mutate=='prefix': m['animations']['idle']['filePrefix']='../escape'
            if mutate=='duration': m['animations']['idle']['frameDuration']=0
            if mutate=='first': m['animations']['idle']['firstFrame']=2
            if mutate=='count': m['animations']['idle']['frames']=257
            requests.append(dict(species='moa',stage=1,base='public/assets/creatures/moa/stage01',manifest=m))
        results = phase.runtime_manifests(ROOT, requests)
        self.assertIn('clips', results[0])
        self.assertEqual(results[0]['clips']['walk'][0], 'public/assets/creatures/moa/stage01/walk/walk_00.png')
        self.assertTrue(all('error' in r for r in results[1:]))

    def test_production_frames_and_missing_actions_are_distinguished(self):
        moa = self.report['characters'][0]
        self.assertEqual(moa['actions']['MOVE']['status'], 'EXISTING_FRAME_REFERENCE')
        self.assertEqual(moa['actions']['BLINK']['status'], 'EXISTING_FRAME_REFERENCE')
        self.assertEqual(moa['actions']['SKILL_CAST']['status'], 'ASSET_REQUIRED')
        self.assertEqual(moa['actions']['SLEEP']['status'], 'ASSET_REQUIRED')
        self.assertEqual(self.report['hooks']['skill']['status'], 'EVENT_CONTRACT_REQUIRED')

    def test_species_proposals_have_different_habits_even_for_same_profile(self):
        rows = [dict(species=r['conceptId'],movementProfile=r['movementProfile']['value'],
                     **{k:r['speciesBehavior'][k] for k in phase.BEHAVIOR_AXES}) for r in self.catalog['monsterConcepts']]
        self.assertEqual(phase.validate_behavior_proposals(rows), [])
        other = copy.deepcopy(rows[0]); other['species']='different'
        self.assertTrue(phase.validate_behavior_proposals([rows[0],other]))
        for axis in phase.BEHAVIOR_AXES:
            broken = copy.deepcopy(rows[0]);del broken[axis]
            self.assertTrue(phase.validate_behavior_proposals([broken]))
        self.assertEqual(len({r['movementIntentProposal'] for r in self.catalog['companionForms']}), 15)

    def test_concept_skills_have_no_server_balance_or_execution_binding(self):
        for r in self.catalog['monsterConcepts']:
            self.assertIsNone(r['skillIdentity']['serverCode'])
            self.assertIsNone(r['skillIdentity']['cooldownTurns'])
            self.assertIsNone(r['rarity'])
            self.assertIsNone(r['spawnTier'])
            self.assertEqual(r['skillIdentity']['execution'], 'SERVER_AUTHORITATIVE')

    def test_path_traversal_symlink_and_wrong_case_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'asset.png').write_bytes(b'x')
            for path in ('../asset.png','/etc/passwd'):
                with self.assertRaises(ValueError): phase.local_file(root,path)
            self.assertIsNone(phase.local_file(root,'ASSET.png'))
            (root/'link.png').symlink_to(root/'asset.png')
            with self.assertRaises(ValueError): phase.local_file(root,'link.png')

    def run_frames(self, manifest, kind='SPRITE_CANDIDATE'):
        return subprocess.run([sys.executable,str(ROOT/'scripts/visual_phase1.py'),'frames',
                               '--manifest',str(manifest),'--species','moa','--stage','1','--kind',kind],
                              text=True,capture_output=True)

    def test_default_concept_cannot_pass_even_if_png_is_well_formed(self):
        result=self.run_frames(ROOT/'public/assets/creatures/moa/stage01/manifest.json','CONCEPT_REFERENCE')
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout)['status'],'ASSET_REQUIRED')

    def test_candidate_validator_cannot_operate_on_production_directory(self):
        result=self.run_frames(ROOT/'public/assets/creatures/moa/stage01/manifest.json')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('separate staging',result.stderr)

    def test_candidate_real_frame_missing_corrupt_and_transparent_empty(self):
        from test_assets import png
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'idle').mkdir()
            manifest={'species':'moa','stage':1,'canvas':{'width':256,'height':256},
                      'anchor':{'x':.5,'y':1},'display':{'width':82},
                      'animations':{'idle':{'frames':1,'frameDuration':100,'loop':True}}}
            path=root/'manifest.json';path.write_text(json.dumps(manifest));frame=root/'idle/idle_00.png'
            result=self.run_frames(path)
            self.assertEqual(json.loads(result.stdout)['status'],'ASSET_REQUIRED')
            self.assertEqual(result.returncode,1)
            frame.write_bytes(b'broken')
            self.assertEqual(json.loads(self.run_frames(path).stdout)['status'],'INVALID_FRAMES')
            frame.write_bytes(png()) # entirely transparent parser fixture is NOT character art
            self.assertEqual(json.loads(self.run_frames(path).stdout)['status'],'INVALID_FRAMES')
            frame.write_bytes((ROOT/'public/assets/creatures/moa/stage01/idle/idle_00.png').read_bytes())
            result=self.run_frames(path);body=json.loads(result.stdout)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(body['status'],'FRAME_FILES_VALID')
            self.assertFalse(body['runtimeActivation'])
            self.assertEqual(body['visualApproval'],'NOT_VERIFIED')

    def test_unsupported_profile_and_duplicate_species_rejected(self):
        r=dict(species='M001',movementProfile='GROUND',**{k:k for k in phase.BEHAVIOR_AXES})
        self.assertTrue(phase.validate_behavior_proposals([]))
        self.assertTrue(phase.validate_behavior_proposals([r,r]))
        r['movementProfile']='NEW_ENGINE'
        self.assertTrue(phase.validate_behavior_proposals([r]))

    def test_identity_and_reference_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'design/visual-reference-v1';directory.mkdir(parents=True)
            data=copy.deepcopy(self.catalog)
            for reference in data['references'].values():
                target=root/reference['path'];target.write_bytes((ROOT/reference['path']).read_bytes())
            path=directory/'catalog.json'
            data['monsterConcepts'][0]['existingMonsterCode']='PIP';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):phase.reference_catalog(root)
            data=copy.deepcopy(self.catalog);data['references']['monsters']['sha256']='0'*64
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):phase.reference_catalog(root)
