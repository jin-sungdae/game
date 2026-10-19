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
    return {'scope':'Isolated candidate review only; existing Production approvals are not overridden',
            'creatures':list(rows.values()),'productionRegistration':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-inventory',action='store_true',help='Refresh only measured Monster PNG counts; never approval or Runtime fields')
    args=parser.parse_args()
    if args.refresh_inventory: refresh_inventory()
    data=build(); p=ROOT/'tests/live/creature-review/catalog.json';p.write_text(json.dumps(data,indent=2)+'\n')
    clips=[c for r in data['creatures'] for c in r['clips']]
    print(json.dumps({'creatures':len(data['creatures']),'clips':len(clips),'automatedPass':sum(c['automated']=='PASS' for c in clips),'needsReviewOrFailed':sum(c['automated']!='PASS' for c in clips)}))
