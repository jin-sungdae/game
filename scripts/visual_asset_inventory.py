"""Read-only full-production visual inventory. Never infers GUI acceptance from files.
Run with --root CHECKOUT; optionally --candidate PNG --reference APPROVED_BASE.
Existing PNG validator is the sole decoder. Does not write assets or runtime registries.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from validate_assets import ROOT, png_errors

STATES = ('NOT_SUPPLIED', 'DESIGN_READY', 'ARTWORK_READY', 'FRAMES_READY',
          'ANIMATION_CONNECTED', 'AUTOMATED_VERIFIED', 'GUI_ACCEPTED')
REQUIRED = ('idle', 'movement', 'turning', 'interaction', 'battle', 'skill', 'hit', 'victory', 'defeat')

def inspect_png(path):
    if not path.is_file():
        return {'status': 'NOT_SUPPLIED', 'errors': ['missing file']}
    bounds, pixels = [], []
    errors = png_errors(path, require_transparency=True, bounds=bounds, pixel_digests=pixels)
    return {'status': 'NOT_SUPPLIED' if errors else 'ARTWORK_READY',
            'errors': errors, 'pixelSha256': pixels[0] if pixels else None, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bounds': bounds}

def candidate(path, reference):
    result, master = inspect_png(path), inspect_png(reference)
    errors = list(result['errors']) + ['reference: '+e for e in master['errors']]
    drift = None
    if not errors:
        a, b = result['bounds'], master['bounds']
        drift = {'centerX': (a[0]+a[2]-b[0]-b[2])/2, 'bottom': a[3]-b[3]}
        if any(drift.values()):
            errors.append('registration differs from approved master')
    return {'candidate': str(path), 'reference': str(reference), 'image': result,
            'referenceImage': master, 'driftPixels': drift, 'errors': errors,
            'automated': 'FAIL' if errors else 'PASS', 'guiAcceptance': 'NOT_VERIFIED',
            'identityReview': 'MANUAL_VISUAL_REVIEW', 'productionEligible': False}

def clips(directory, identity=None):
    path = directory/'manifest.json'
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text())
    metadata_errors = []
    if identity is not None:
        species, stage = identity
        if manifest.get('species') != species or type(manifest.get('stage')) is not int or manifest.get('stage') != stage:
            metadata_errors.append('species/stage mismatch')
        if manifest.get('canvas') != {'width':256, 'height':256}:
            metadata_errors.append('canvas must be 256x256')
        if manifest.get('anchor') != {'x':.5, 'y':1}:
            metadata_errors.append('anchor must be bottom-center')
        width = manifest.get('display', {}).get('width')
        if type(width) not in (int, float) or not math.isfinite(width) or width <= 0:
            metadata_errors.append('invalid display width')
    result = {}
    for name, clip in manifest.get('animations', {}).items():
        if not name.replace('_','').replace('-','').isalnum():
            raise ValueError('invalid clip path')
        count = clip.get('frames')
        if type(count) is not int or not 1 <= count <= 256:
            raise ValueError('invalid frame count')
        first = clip.get('firstFrame', 1 if name in ('jump','hover','fly','glide','float','settle') else 0)
        prefix = clip.get('filePrefix', name)
        if type(first) is not int or first not in (0,1) or not prefix.replace('_','').replace('-','').isalnum():
            raise ValueError('invalid frame naming')
        files = [directory/name/f'{prefix}_{i:02}.png' for i in range(first, first+count)]
        images = [inspect_png(p) for p in files]
        errors = list(metadata_errors)
        duration = clip.get('frameDuration')
        if identity is not None and (type(duration) not in (int,float) or not math.isfinite(duration) or duration <= 0 or type(clip.get('loop')) is not bool):
            errors.append('invalid timing/loop')
        hashes = [x.get('pixelSha256') for x in images if not x['errors']]
        if count < 2:
            errors.append('single frame is artwork, not continuous animation')
        if hashes and len(hashes) == count and len(set(hashes)) == 1:
            errors.append('identical decoded frames are not animation')
        ready = not errors and all(not item['errors'] for item in images)
        result[name] = {'status':'FRAMES_READY' if ready else 'NOT_SUPPLIED',
                        'errors':errors, 'frameEvidence':[{'file':str(p), **x} for p,x in zip(files,images)],
                        'expectedFrames': count, 'validFrames':sum(not x['errors'] for x in images),
                        'missingOrInvalid':[str(p) for p,x in zip(files,images) if x['errors']],
                        'guiAcceptance':'NOT_VERIFIED'}
    return result

def delivery_contract(species, stage, available):
    # Delivery preparation only: never install placeholders into public or the registry.
    actions = {}
    for action, clip in [('IDLE','idle'),('MOVE','walk'),('TURN','turn'),('INTERACT','react')]:
        evidence = available.get(clip, {})
        actions[action] = {
            'clip':clip, 'status':'FRAMES_READY' if evidence.get('status')=='FRAMES_READY' else 'ASSET_REQUIRED',
            'frames':evidence.get('expectedFrames'), 'runtimeConnection':'NOT_VERIFIED',
            'framePath':f'{clip}/{clip}_NN.png',
        }
    return {'species':species,'stage':stage,
            'manifestPath':f'public/assets/creatures/{species}/stage{stage:02}/manifest.json',
            'canvas':{'width':256,'height':256}, 'anchor':{'x':.5,'y':1},
            'actions':actions, 'productionEligible':False,
            'identityReview':'MANUAL_VISUAL_REVIEW', 'registrationReview':'MANUAL_VISUAL_REVIEW',
            'guiAcceptance':'DEFERRED_GUI'}

def inventory(root):
    companions = []
    for species in ('moa','ruu','nox'):
        for stage in range(1,6):
            directory=root/'public/assets/creatures'/species/f'stage{stage:02}'
            available=clips(directory, (species,stage))
            mapped={key:available.get({'movement':'walk','interaction':'react'}.get(key,key),
                                     {'status':'NOT_SUPPLIED','guiAcceptance':'NOT_VERIFIED'}) for key in REQUIRED}
            companions.append({'species':species,'stage':stage,'base':inspect_png(directory/'base.png'),
                               'requiredAnimations':mapped,'suppliedClips':available,
                               'deliveryContract':delivery_contract(species,stage,available)})
    registry=json.loads((root/'src/entities/monsters.json').read_text())
    monsters=[]
    for row in json.loads((root/'src/entities/monster-dex.json').read_text()):
        code=row['monsterCode']; entry=registry.get(code,{})
        # Unregistered provisional identities stay absent; no substitution with another species.
        directory=root/'public'/entry.get('assetRoot',f'assets/monsters/{code.lower()}').lstrip('/')
        monsters.append({'code':code,'enabled':row['enabled'],'movementProfile':row['movementProfile'],
                         'base':inspect_png(directory/'base.png'),'clips':clips(directory)})
    result = {'companions':companions,'monsters':monsters,
            'guiAcceptance':'NOT_VERIFIED',
            'note':'File readiness only. Runtime connection, identity and actual GUI require separate evidence. Missing frame counts are unknown where no approved clip contract exists.'}
    return json.loads(json.dumps(result).replace(str(root.resolve())+'/', ''))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--candidate',type=Path);p.add_argument('--reference',type=Path)
    args=p.parse_args()
    if bool(args.candidate) != bool(args.reference): p.error('candidate and reference required together')
    result=candidate(args.candidate,args.reference) if args.candidate else inventory(args.root)
    print(json.dumps(result,indent=2))
    if args.candidate and result['automated']=='FAIL': raise SystemExit(1)
