#!/usr/bin/env python3
"""Read-only asset inspection; writes only an isolated review catalog, never registries."""
import argparse
import json
import re
from pathlib import Path
from validate_assets import png_errors

ROOT=Path(__file__).resolve().parents[1]

def inventory_counts(root=ROOT):
    monsters=root/'design/production-batches/monsters'
    return {'allCandidatePng':len(list(monsters.rglob('*.png'))),
            'sourcePngIncludingRecovery':len(list(monsters.rglob('source*.png')))}

def refresh_inventory():
    path=ROOT/'design/creature-production-queue.json'
    queue=json.loads(path.read_text())
    queue['candidateInventory'].update(inventory_counts())
    path.write_text(json.dumps(queue,indent=2,ensure_ascii=False)+'\n')

# Supply inspection is deliberately separate from runtime/approval claims.
ACTION_CLIPS = {
    'IDLE': ('idle',), 'BREATH': ('breath',), 'BLINK': ('blink',),
    'LOOK': ('look',), 'MOVE': ('walk', 'run', 'fly', 'float', 'flow', 'edge_move'),
    'TURN': ('turn',), 'REST': ('sit', 'rest'), 'SLEEP': ('sleep',),
    'CURSOR_REACT': ('cursor_react',), 'INTERACT': ('react', 'interact'),
    'ATTACK': ('attack',), 'SKILL_CAST': ('skill_cast',), 'HIT': ('hit',),
    'VICTORY': ('victory',), 'DEFEAT': ('defeat',), 'EVOLUTION': ('evolution',),
}

def manifest_supply(path):
    if not path or not path.is_file(): return {}
    manifest=json.loads(path.read_text())
    result={}
    for name, clip in manifest.get('animations', {}).items():
        first=clip.get('firstFrame', 0); count=clip.get('frames', 0)
        prefix=clip.get('filePrefix', name)
        files=[path.parent/name/f'{prefix}_{i:02}.png' for i in range(first, first+count)]
        result[name]={'declaredFrames':count, 'presentFrames':sum(p.is_file() for p in files),
                      'completeFileSet':bool(files) and all(p.is_file() for p in files)}
    return result

def coverage(actions, clips, supply):
    ready=connected=present=candidates=automated=pending=failed=missing=gui=complete=0
    for action in actions:
        name=action['action']
        matching=[c for c in clips if c['action'].upper()==name]
        supplied=any(supply.get(c, {}).get('completeFileSet', False) for c in ACTION_CLIPS.get(name, ()))
        is_ready=action['animationStatus']=='ANIMATION_READY'
        is_connected=action['runtimeStatus']=='RUNTIME_CONNECTED'
        ready+=is_ready; connected+=is_connected; present+=supplied
        candidates+=bool(matching)
        automated+=any(c['automated']=='PASS' for c in matching)
        pending+=bool(matching) and action.get('artworkReview')!='USER_APPROVED'
        failed+=action['animationStatus']=='VALIDATION_FAILED' or any(c['automated']!='PASS' for c in matching)
        missing+=not supplied and not matching
        gui+=action.get('guiStatus')!='PASS'
        complete+=is_ready and is_connected and supplied and action.get('guiStatus')=='PASS'
    return {'requiredActions':len(actions), 'recordedReadyActions':ready,
            'recordedRuntimeActions':connected, 'manifestFileSetsPresent':present,
            'candidateActions':candidates, 'automatedCandidateActions':automated,
            'artworkReviewPendingActions':pending, 'validationFailedActions':failed,
            'missingFrameSetActions':missing, 'guiPendingActions':gui, 'completeActions':complete}

def add_coverage(data):
    companions=json.loads((ROOT/'src/entities/companions.json').read_text())
    monsters=json.loads((ROOT/'src/entities/monsters.json').read_text())
    for row in data['creatures']:
        uri=None
        if row['id'].startswith('companion:'):
            _,species,stage=row['id'].split(':')
            uri=companions.get(species,{}).get('stages',{}).get(stage)
        elif row.get('productionSpeciesId') in monsters:
            uri=monsters[row['productionSpeciesId']]['assetRoot']+'/manifest.json'
        supply=manifest_supply(ROOT/'public'/uri.lstrip('/')) if uri else {}
        row['coverage']=coverage(row['actions'],row['clips'],supply)
        row['manifestSupply']=supply
    data['coverageSummary']={key:sum(r['coverage'][key] for r in data['creatures'])
                             for key in data['creatures'][0]['coverage']}
    data['coverageSummary']['creatures']=len(data['creatures'])
    data['coverageSummary']['completeCreatures']=sum(r['coverage']['completeActions']==r['coverage']['requiredActions'] for r in data['creatures'])
    data['coverageScope']='Counts are per action, not per candidate version. File presence is not PNG validation, artwork approval, native runtime or GUI proof. Completion requires all four recorded readiness/runtime/file/GUI conditions.'
    # Existing 30 DB identities are audited separately, never added to the 115 concept/form queue.
    dex=json.loads((ROOT/'src/entities/monster-dex.json').read_text())
    data['legacyProductionAudit']=[]
    for monster in dex:
        code=monster['monsterCode']; registered=monsters.get(code)
        supply=manifest_supply(ROOT/'public'/registered['assetRoot'].lstrip('/')/'manifest.json') if registered else {}
        data['legacyProductionAudit'].append({'speciesId':code,'movementProfile':monster['movementProfile'],
            'conceptMapping':'NOT_ASSUMED','registeredArtwork':bool(registered),'manifestSupply':supply,
            'runtimeCoverage':'NOT_INFERRED_FROM_FILES','fullActionGui':'NOT_VERIFIED'})
    return data

def refresh_coverage(data):
    path=ROOT/'design/creature-production-queue.json'
    queue=json.loads(path.read_text()); by_id={r['id']:r for r in data['creatures']}
    for row in queue['creatures']: row['animationCoverage']=by_id[row['creatureId']]['coverage']
    queue['animationCoverageSummary']=data['coverageSummary']
    queue['animationCoverageScope']=data['coverageScope']
    queue['legacyProductionAudit']=data['legacyProductionAudit']
    path.write_text(json.dumps(queue,indent=2,ensure_ascii=False)+'\n')

def build():
    queue=json.loads((ROOT/'design/creature-production-queue.json').read_text())
    rows={r['creatureId']:{'id':r['creatureId'],'productionSpeciesId':r.get('productionSpeciesId'),
          'basePath':('/'+r['basePath']) if r.get('basePath') else None,
          'productionStatus':r['productionStatus'],'actions':r['actions'],'clips':[]} for r in queue['creatures']}
    for directory in sorted((ROOT/'design').glob('**/rigged/*')):
        if not directory.is_dir(): continue
        frames=sorted(directory.glob('*.png'))
        if not frames: continue
        rel=directory.relative_to(ROOT).as_posix()
        monster=re.search(r'/(M\d{3})/',rel)
        companion=re.search(r'/(moa|ruu|nox)/stage(\d+)/',rel)
        identity=monster[1] if monster else f'companion:{companion[1]}:{int(companion[2])}' if companion else None
        if identity not in rows: continue
        parent=directory.parent.parent
        contract=parent/'candidate-clip.json'
        spec=json.loads(contract.read_text()).get('clip',{}) if contract.exists() else {}
        action=directory.name
        if spec.get('name','').lower()!=action: spec={}
        evidence=parent/'rig-evidence.json'
        if not evidence.exists(): evidence=parent/f'{action}-rig-evidence.json'
        rig=json.loads(evidence.read_text()) if evidence.exists() else {}
        expected=spec.get('frames') or len(rig.get('frames',[]))
        errors=[]; hashes=[]; bounds=[]
        if not expected: errors.append('EXPECTED_FRAME_COUNT_NOT_VERIFIED')
        elif expected!=len(frames): errors.append('FRAME_COUNT_MISMATCH')
        for n,frame in enumerate(frames):
            b=[]; e=png_errors(frame,True,b,hashes); errors.extend(f'{frame.name}: {v}' for v in e); bounds.append(b)
            if frame.name!=f'{action}_{n:02}.png': errors.append(f'{frame.name}: NONCANONICAL_SEQUENCE')
        if len(set(hashes))!=len(frames): errors.append('DUPLICATE_OR_UNDECODABLE_PIXELS')
        if bounds and any(b!=bounds[0] for b in bounds): errors.append('BOUNDS_VARY_REVIEW_REQUIRED')
        rows[identity]['clips'].append({'action':action,'directory':'/'+rel,'urls':['/'+f.relative_to(ROOT).as_posix() for f in frames],
            'frameCount':len(frames),'frameDuration':spec.get('frameDuration',400),
            'timingSource':'candidate contract' if spec.get('frameDuration') else 'preview only 400ms; production timing unapproved',
            'automated':'PASS' if not errors else 'VALIDATION_FAILED','errors':errors,'bounds':bounds,
            'pixelHashes':hashes,'artwork':'HUMAN_REVIEW_REQUIRED','runtimeEnabled':False})
    return add_coverage({'scope':'Isolated candidate review only; existing Production approvals are not overridden',
            'creatures':list(rows.values()),'productionRegistration':False})

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-inventory',action='store_true',help='Refresh only measured Monster PNG counts; never approval or Runtime fields')
    parser.add_argument('--refresh-coverage',action='store_true',help='Refresh derived per-action coverage in the existing Ledger; never approval or Runtime fields')
    args=parser.parse_args()
    if args.refresh_inventory: refresh_inventory()
    data=build()
    if args.refresh_coverage: refresh_coverage(data)
    p=ROOT/'tests/live/creature-review/catalog.json';p.write_text(json.dumps(data,indent=2)+'\n')
    clips=[c for r in data['creatures'] for c in r['clips']]
    print(json.dumps({'creatures':len(data['creatures']),'clips':len(clips),'automatedPass':sum(c['automated']=='PASS' for c in clips),'needsReviewOrFailed':sum(c['automated']!='PASS' for c in clips)}))
