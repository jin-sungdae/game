"""Read-only M071-M075 handoff audit; stdout is session evidence, never a ledger."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_creature_review as review
from visual_asset_inventory import inspect_png

IDS = tuple(f'M{i:03}' for i in range(71, 76))
EXTRA = ('JUMP', 'FLY', 'HOVER', 'LAND', 'CHARGE', 'RECOVERY')
RIG = ('RIG_LAYER_REQUIRED: flattened rigid body has no reusable isolated part masks, '
       'joint pivots or occluded backing; existing organic weighted displacement would deform plates')
REASONS = {
    'M071': RIG,
    'M072': 'APPEARANCE_DRIFT: upright rune automaton reference versus quadrupedal BASE; human identity decision required',
    'M073': RIG,
    'M074': 'IDENTITY_REVIEW_REQUIRED: chained vessel STATIC proposal versus multi-legged mechanical BASE',
    'M075': RIG + '; external ornaments connect at upper and lower body',
}
NEEDS = {
    'IDLE': 'rigid joint settling and core mechanism',
    'BREATH': 'approved mechanical core cycle; no organic plate deformation',
    'BLINK': 'approved lens/shutter masks; no invented organic eyelids',
    'LOOK': 'head/lens pivot and occluded backing',
    'MOVE': 'articulated support/contact cycle and approved locomotion',
    'TURN': 'side/back surfaces and rigid joint pivots',
    'REST': 'articulated rest pose and contact anchors',
    'SLEEP': 'approved dormant mechanical pose and lens state',
    'CURSOR_REACT': 'species-specific head/lens/arm response',
    'INTERACT': 'separated articulated gesture parts',
    'ATTACK': 'articulated anticipation/impact/recovery poses',
    'SKILL_CAST': 'approved skill identity and articulated charge/release poses',
    'HIT': 'rigid recoil pose and stable contacts',
    'VICTORY': 'species-specific articulated celebration',
    'DEFEAT': 'articulated collapse/dormant pose and ground contacts',
    'JUMP': 'approved takeoff/support/landing articulation',
    'FLY': 'approved flight anatomy and locomotion contract',
    'HOVER': 'approved suspension mechanism and locomotion contract',
    'LAND': 'approved airborne-to-ground contact transition',
    'CHARGE': 'approved charge meaning and articulated anticipation',
    'RECOVERY': 'valid preceding action and articulated recovery to rest',
}

def main():
    queue_path = ROOT / 'design/creature-production-queue.json'
    original = queue_path.read_bytes()
    queue = json.loads(original)
    concepts = {m['conceptId']: m for m in json.loads(
        (ROOT / 'design/visual-reference-v1/catalog.json').read_text())['monsterConcepts']}
    # Exercise the existing refresh functions against a disposable ledger only.
    # The user explicitly prohibits writing the shared ledger or review catalog.
    with tempfile.TemporaryDirectory(prefix='luma-asset18-ledger-') as temporary:
        staging = Path(temporary)
        (staging / 'design').mkdir()
        scoped = dict(queue)
        scoped['creatures'] = [m for m in queue['creatures'] if m['creatureId'] in IDS]
        (staging / 'design/creature-production-queue.json').write_text(json.dumps(scoped))
        (staging / 'src').symlink_to(ROOT / 'src', target_is_directory=True)
        (staging / 'public').symlink_to(ROOT / 'public', target_is_directory=True)
        for identity in IDS:
            for relative in (f'design/production-batches/monsters/batch08/{identity}',
                             f'design/production-batches/action-followup/{identity}'):
                source = ROOT / relative
                if source.is_dir():
                    target = staging / relative
                    target.mkdir(parents=True)
                    # rglob need not follow directory symlinks: mirror file links explicitly.
                    for file in source.rglob('*'):
                        if file.is_file():
                            link = target / file.relative_to(source)
                            link.parent.mkdir(parents=True, exist_ok=True)
                            link.symlink_to(file)

        saved_root = review.ROOT
        review.ROOT = staging
        try:
            catalog = review.build()
            measured = {m['id']: m for m in catalog['creatures']}
            review.refresh_coverage(catalog)
            # inventory_counts has an original-root default and is read-only.
            review.refresh_inventory()
            refreshed = json.loads((staging / 'design/creature-production-queue.json').read_text())
        finally:
            review.ROOT = saved_root
    rows = []
    for monster in queue['creatures']:
        identity = monster['creatureId']
        if identity not in IDS:
            continue
        source = ROOT / f'design/production-batches/monsters/batch08/{identity}/base-v2.png'
        png = inspect_png(source)
        concept = concepts[identity]
        rigs = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'design').rglob('rig-*.cjs')
                      if identity in p.parts)
        actions = []
        for entry in monster['actions'] + [{'action': a, 'animationStatus': 'NOT_SUPPLIED'} for a in EXTRA]:
            action = entry['action']
            actions.append({'action': action, 'existingStatus': entry['animationStatus'],
                            'sessionStatus': 'BLOCKED', 'existingBlockReason': entry.get('blockReason'),
                            'reason': REASONS[identity], 'requiredInput': NEEDS[action],
                            'candidatePath': entry.get('candidatePath'),
                            'repairAttempted': False, 'newPngs': 0, 'newClips': 0})
        rows.append({'monster': identity, 'base': str(source.relative_to(ROOT)),
                     'baseStatus': monster['baseStatus'], 'pngValidation': png,
                     'observedForm': concept['observedForm'],
                     'proposedProfiles': {k: concept[k] for k in ('personality','movementProfile','speciesBehavior')},
                     'ledgerProfiles': {k: monster[k] for k in ('personality','movementProfile','speciesBehavior')},
                     'existingRigScripts': rigs, 'measuredCoverage': measured[identity]['coverage'],
                     'actions': actions, 'productionSpeciesId': monster['productionSpeciesId'],
                     'anchor': 'UNAPPROVED_NO_CLIP_MANIFEST',
                     'appearanceDrift': 'KNOWN_FAILURE_PRESERVED' if identity == 'M072' else 'HUMAN_REVIEW_REQUIRED',
                     'frameContinuity': 'NOT_RUN_NO_FRAMES', 'gui': 'DEFERRED_GUI'})
    assert queue_path.read_bytes() == original, 'shared ledger changed'
    print(json.dumps({'sessionId': 'LUMA-ASSET-18', 'status': 'BLOCKED_HUMAN_REVIEW_REQUIRED',
        'auditedCommit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'ledgerSha256': hashlib.sha256(original).hexdigest(),
        'repairIterations': queue['repairIterations'], 'repairLimit': queue['repairLimit'],
        'repairPolicy': 'Inherited exhausted budget preserved; no resets, retries or failed-candidate recovery',
        'newPngs': 0, 'newClips': 0, 'monsters': rows,
        'inventoryRecomputed': refreshed['candidateInventory'],
        'refreshScope': 'Existing refresh functions on disposable five-monster ledger; coverage scoped to M071-M075, inventory reads original repository; shared ledger/catalog untouched',
        'productionApproval': 'HUMAN_REVIEW_REQUIRED', 'runtimeConnected': False,
        'nativeMacOS': 'DEFERRED_GUI', 'nativeWindows': 'DEFERRED_GUI',
        'integrationRequests': [
            'Resolve M072 upright/quadruped and M074 vessel/multi-legged identity conflicts before artwork work.',
            'Supply approved rigid part masks, pivots, occluded surfaces and contact anchors for M071/M073/M075.',
            'Preserve M071 HIT, M072 TURN and M073 HIT failed sources and inherited 3/3 limit; human review required.',
            'Review proposed Personality, MovementProfile, SpeciesBehavior and skill identity without automatic activation.',
            'Integration owner should reconcile this audit with shared ledger/catalog; no ready actions to register.',
            'Only after artwork/motion/identity approval may integration owner change Animation Manifest, Production Registry or Runtime.'
        ],
        'nextResume': 'After approved rigid layers are supplied, first attempt M071 IDLE mechanical settling; then M073 IDLE. Keep exhausted HIT/TURN failures untouched. Reassess all remaining actions independently.',
        'completion': 'No animation completed; Draft PR is a blocked handoff, not creature completion'
    }, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
