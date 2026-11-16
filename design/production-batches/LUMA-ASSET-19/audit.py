"""Read-only source audit; writes only this session's integration request."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from visual_asset_inventory import inspect_png
from build_creature_review import inventory_counts, coverage

IDS = [f'M{i:03}' for i in range(76, 81)]
queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
catalog = json.loads((ROOT / 'design/visual-reference-v1/catalog.json').read_text())

def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)

concepts = {r['conceptId']: r for r in objects(catalog) if r.get('conceptId') in IDS and 'observedForm' in r}
tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
requirements = {
    'IDLE': 'Separate rigid joint/core layers and pivots for a mechanical resting cycle.',
    'BREATH': 'Mechanical cycle definition and independent core/vent layers; organic plate scaling is unsuitable.',
    'BLINK': 'Defined eye/shutter anatomy and closed/open artwork; do not invent eyelids on rings.',
    'LOOK': 'Independent head/sensor rig and covered backing for directed attention.',
    'MOVE': 'Locomotion/contact definition plus joint layers; whole-image translation is insufficient.',
    'TURN': 'Side surfaces, rigid pivots and occluded backing; no whole-image mirror or rotation.',
    'REST': 'Articulated settling pose with defined mechanical resting state.',
    'SLEEP': 'Defined dormant anatomy and articulated transition; dimming alone is insufficient.',
    'CURSOR_REACT': 'Directed sensor/body articulation with anticipation and return.',
    'INTERACT': 'Species-specific joint gesture with return to resting anatomy.',
    'ATTACK': 'Articulated anticipation, strike and recovery; preserve server-authoritative contract.',
    'SKILL_CAST': 'Defined mechanical cast gesture and skill motif; glow alone is insufficient.',
    'HIT': 'Rigid recoil articulation with covered backing; no organic plate deformation.',
    'VICTORY': 'Distinct articulated victory gesture and stable ending.',
    'DEFEAT': 'Defined disabled posture and rigid contact geometry.',
}
anatomy = {
    'M076': 'Flattened rune ring: overlapping segments/core, no separated pivot layers or side surfaces. Existing TURN failed at repair 3/3.',
    'M077': 'Preserved failed BASE depicts a rabbit-like quadruped rather than the crowned upright automaton; identity decision precedes any derived animation.',
    'M078': 'Flattened quadruped armor overlaps shoulder/hip joints; independent plates, limb pivots and occluded backing are absent.',
    'M079': 'Flattened oval gate side bosses overlap frame; side surfaces and separated mechanical pivots are absent.',
    'M080': 'Orbital core connects to spindle/ring; occluded surfaces and separated pivots are absent, with existing ring anatomy review unresolved.',
}
rows = []
for ident in IDS:
    ledger = next(r for r in queue['creatures'] if r['creatureId'] == ident)
    concept = concepts[ident]
    files = [p for p in tracked if ident in Path(p).parts]
    rigs = [p for p in files if any(s in Path(p).name.lower() for s in ('rig', 'mask', 'layer', 'pivot'))]
    clips = [p for p in files if Path(p).name in ('candidate-clip.json', 'manifest.json')]
    if rigs or clips:
        raise RuntimeError(f'{ident}: new rig/clip supply requires reassessment: {rigs + clips}')
    base = f'design/production-batches/monsters/batch08/{ident}/base-v2.png'
    measurement = inspect_png(ROOT / base)
    width, height, depth, color = struct.unpack('>IIBB', (ROOT / base).read_bytes()[16:26])
    actions = []
    for action in ledger['actions']:
        name = action['action']
        actions.append({'action': name, 'previousStatus': action['animationStatus'],
                        'status': 'BLOCKED', 'reason': action.get('blockReason', anatomy[ident]),
                        'requiredInput': requirements[name], 'newFrames': 0, 'newClips': 0,
                        'failureRecoveryAttempted': False})
    optional = []
    for name in ['JUMP', 'FLY', 'HOVER', 'LAND', 'CHARGE', 'RECOVERY']:
        if name in ('FLY', 'HOVER') and ident != 'M080':
            status, reason = 'APPLICABILITY_REVIEW_REQUIRED', 'No approved flight/hover anatomy; proposed profile is ' + concept['movementProfile']['value']
        elif name in ('JUMP', 'LAND') and ident in ('M076', 'M079'):
            status, reason = 'APPLICABILITY_REVIEW_REQUIRED', 'STATIC proposal has no approved jumping/landing mechanism.'
        else:
            status, reason = 'BLOCKED', anatomy[ident]
        optional.append({'action': name, 'status': status, 'reason': reason,
                         'requiredInput': 'Approve applicability and supply articulated contact/flight/charge/recovery poses before producing frames.'})
    rows.append({'creatureId': ident, 'observedForm': concept['observedForm'],
                 'basePath': base, 'baseStatus': ledger['baseStatus'],
                 'baseMeasurement': {**measurement, 'width': width, 'height': height,
                                     'bitDepth': depth, 'colorType': color},
                 'anchor': {'expected': {'x': .5, 'y': 1}, 'status': 'NOT_VERIFIED_NO_CLIP_MANIFEST'},
                 'appearanceDrift': 'EXISTING_VALIDATION_FAILED' if ident == 'M077' else 'HUMAN_REVIEW_REQUIRED',
                 'frameContinuity': 'NOT_RUN_NO_FRAME_SET',
                 'productionSpeciesId': ledger['productionSpeciesId'],
                 'personality': {'proposal': concept['personality'], 'ledger': ledger['personality']},
                 'movementProfile': {'proposal': concept['movementProfile'], 'ledger': ledger['movementProfile']},
                 'speciesBehavior': {'proposal': concept['speciesBehavior'], 'ledger': ledger['speciesBehavior']},
                 'anatomyAssessment': anatomy[ident], 'trackedSourceFiles': files,
                 'existingRigFiles': rigs, 'existingClipFiles': clips,
                 'coverage': coverage(ledger['actions'], [], {}),
                 'actions': actions, 'optionalActions': optional})
protected = ['design/creature-production-queue.json', 'design/production-completion-ledger.json',
             'design/monster-identity-review.json', 'design/visual-reference-v1/catalog.json']
report = {'sessionId': 'LUMA-ASSET-19', 'baseCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'branch': 'codex/assets-m076-m080', 'status': 'BLOCKED', 'fullCreatureProductionComplete': False,
          'newPngCount': 0, 'newClipCount': 0, 'requiredActionsReviewed': 75, 'optionalActionsReviewed': 30,
          'repairIterations': queue['repairIterations'], 'repairLimit': queue['repairLimit'],
          'repairAttemptsThisSession': 0, 'failedCandidatesRecovered': False,
          'productionApproval': 'HUMAN_REVIEW_REQUIRED', 'runtimeConnected': False,
          'macOS': 'DEFERRED_GUI', 'windows': 'DEFERRED_GUI',
          'rigReuseAssessment': 'Existing weighted inverse RGBA displacement reviewed (M001 rig-look.cjs); not a rigid joint layer rig. No new renderer or invented species anatomy.',
          'inventory': inventory_counts(), 'inventoryMethod': 'Existing read-only inventory_counts/coverage functions; mutating refresh flags omitted to preserve shared Ledger and catalog.',
          'protectedSourceSha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected},
          'monsters': rows,
          'integrationRequests': [
              {'id': 'IR19-1', 'owner': 'Artwork/identity reviewer', 'request': 'Resolve M077 crowned automaton versus quadruped BASE and M080 ring anatomy; approve species mapping and mechanical behavior definitions. Preserve failed sources and 3/3 cap.'},
              {'id': 'IR19-2', 'owner': 'Rig/artwork integration', 'request': 'Supply species-specific independent rigid masks, pivot coordinates, covered backing and side/closed/rest poses for M076/M078/M079/M080; M077 only after identity resolution.'},
              {'id': 'IR19-3', 'owner': 'Completion Ledger integration', 'request': 'Reconcile this 75-action audit and 30 optional-action reviews using existing refresh inventory/coverage tools; keep every completion/approval flag unchanged until evidence exists.'},
              {'id': 'IR19-4', 'owner': 'Animation/Production integration', 'request': 'No clip available for Manifest, Production Registry or Runtime registration. After artwork/motion approval, validate anchors/continuity and perform macOS/Windows GUI QA before integration.'}],
          'nextResumePoint': 'After IR19-1/IR19-2 inputs, inspect M078 independent rigid joint layers and produce one IDLE cycle, validate, then advance through the remaining independent actions. M076 TURN remains blocked at repair 3/3; do not reset retry budget.'}
(OUT/'integration-request.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'sessionId': report['sessionId'], 'required': 75, 'optional': 30, 'newPng': 0, 'newClip': 0, 'basePngErrors': {r['creatureId']: r['baseMeasurement']['errors'] for r in rows}}))
