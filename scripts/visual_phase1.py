"""Read-only Phase 1 delivery planner. Never writes assets, registries, or runtime state.

python3 scripts/visual_phase1.py inventory > /tmp/luma-missing-assets.json
python3 scripts/visual_phase1.py frames --manifest /path/manifest.json --species moa --stage 2
Concepts may be catalogued, but never satisfy sprite delivery or enable gameplay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from sync_animation_manifests import read
from validate_assets import png_errors

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ('IDLE', 'BREATH', 'BLINK', 'LOOK_AROUND', 'MOVE', 'TURN', 'REST', 'SLEEP',
           'CURSOR_REACT', 'INTERACT', 'ATTACK', 'SKILL_CAST', 'HIT', 'VICTORY', 'DEFEAT', 'EVOLUTION')
# Existing clip candidates only. This is not a runtime state resolver or activation map.
CANDIDATES = {'IDLE': ['idle', 'hover', 'flicker'], 'BREATH': ['breath'], 'BLINK': ['blink'],
              'LOOK_AROUND': ['look'], 'MOVE': ['walk', 'move', 'jump', 'fly', 'float', 'edge_move', 'flow'],
              'TURN': ['turn'], 'REST': ['sit'], 'SLEEP': ['sleep'], 'CURSOR_REACT': ['react']}
BEHAVIOR_AXES = ('frequency', 'preparation', 'transition', 'reaction')
HOOKS = {
    'behavior': ['src-tauri/src/companion/mod.rs:CompanionController',
                 'src-tauri/src/companion/config.rs:living_config',
                 'src-tauri/src/companion/selection.rs:weights',
                 'src-tauri/src/monster_behavior.rs:Controller::poll',
                 'src-tauri/src/monster_behavior/living.rs:Expression::for_species'],
    'movement': ['src-tauri/src/movement/mod.rs:MovementController',
                 'src-tauri/src/presentation/animation.rs:Motion', 'src/animation/pilot.ts:CharacterAnimator'],
    'animation': ['src/animation/model.ts:parseManifest/frameUrls', 'src/animation/loader.ts:AssetLoader',
                  'src/animation/controller.ts:AnimationController', 'src/animation/clock.ts:AnimationClock'],
    'combat': ['src-tauri/src/presentation/mod.rs:Controller::battle', 'src/presentation/model.ts:effectFor'],
    'skill': {'status': 'EVENT_CONTRACT_REQUIRED', 'evidence': 'src/types/entity.ts:Visual',
              'reason': 'No SKILL_CAST phase or skill identity in current desktop Visual; do not infer it from PLAYER_ATTACK.'},
    'evolution': ['src/types/entity.ts:EvolutionPresentation', 'src-tauri/src/backend/evolution.rs'],
}


def runtime_manifests(root, requests):
    """Compile and invoke the existing engine parser and URL builder, not a second implementation."""
    with tempfile.TemporaryDirectory(prefix='luma-manifest-contract-') as temp:
        subprocess.run([str(root/'node_modules/.bin/tsc'), 'src/animation/model.ts', '--outDir', temp,
                        '--resolveJsonModule', '--esModuleInterop', '--module', 'commonjs', '--target',
                        'ES2022', '--strict', '--skipLibCheck'], cwd=root, check=True, capture_output=True)
        code = """
const fs=require('node:fs'); const {parseManifest,frameUrls}=require(process.argv[1]);
const result=JSON.parse(fs.readFileSync(0,'utf8')).map(r=>{
 try {const m=parseManifest(r.manifest,r.species,r.stage);
 return {clips:Object.fromEntries(Object.entries(m.animations).map(([n,c])=>[n,frameUrls(r.base,n,c)]))};}
 catch(e){return {error:String(e.message)}}
}); process.stdout.write(JSON.stringify(result));
"""
        result = subprocess.run(['node', '-e', code, str(Path(temp)/'animation/model.js')],
                                input=json.dumps(requests), text=True, capture_output=True, check=True)
        return json.loads(result.stdout)


def local_file(root, relative):
    path = root/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('path escapes source root: '+relative)
    # Enforce exact case even on case-insensitive host filesystems.
    current = root
    for part in Path(relative).parts:
        if current.is_dir() and part not in {p.name for p in current.iterdir()}:
            return None
        current /= part
        if current.is_symlink():
            raise ValueError('symlink is not an asset: '+relative)
    return path if path.is_file() else None


def inspect_frames(root, requests):
    results = runtime_manifests(root, requests)
    cache = {}
    for request, result in zip(requests, results):
        if 'error' in result:
            result.update(status='INVALID_MANIFEST', clips={})
            continue
        m = request['manifest']
        if m.get('canvas') != {'width': 256, 'height': 256} or not result['clips']:
            result.update(status='INVALID_MANIFEST', error='Delivery requires a nonempty 256x256 manifest', clips={})
            continue
        checked = {}
        for clip, urls in result['clips'].items():
            missing, errors = [], []
            for relative in urls:
                path = local_file(root, relative)
                if path is None:
                    missing.append(relative)
                else:
                    if relative not in cache:
                        cache[relative] = png_errors(path, require_transparency=True, bounds=[])
                    errors.extend(relative+': '+e for e in cache[relative])
            checked[clip] = {'status': 'INVALID_FRAMES' if errors else 'ASSET_REQUIRED' if missing else 'FRAME_FILES_VALID',
                             'frames': urls, 'missing': missing, 'errors': errors}
        result['clips'] = checked
        result['status'] = 'INSPECTED'
    return results


def existing_identities(root):
    companions = read(root/'src/entities/companions.json')
    monsters = read(root/'src/entities/monster-dex.json')
    registry = read(root/'src/entities/monsters.json')
    rows = []
    for species in ('moa', 'ruu', 'nox'):
        d = companions[species]
        for stage in range(1, 6):
            rows.append({'key': f'companion:{species}:{stage}', 'species': species, 'stage': stage,
                         'name': d.get('stageNames', {}).get(str(stage), d['name'] if stage == 1 else None),
                         'assetRoot': f'public/assets/creatures/{species}/stage{stage:02d}',
                         'identityStatus': 'EXISTING_SPECIES_STAGE_SLOT',
                         'runtimeRegistered': str(stage) in d['stages'],
                         'personality': {'identity': d['identity'], 'palette': d['palette']},
                         'behaviorStatus': 'EXISTING_PARTIAL' if species == 'moa' and stage <= 3 else 'BEHAVIOR_APPROVAL_REQUIRED'})
    seen_codes, seen_roots = set(), set()
    for m in monsters:
        code, asset = m['monsterCode'], m['assetIdentity']
        if not re.fullmatch('[a-z][a-z0-9_]*', asset) or code in seen_codes or asset in seen_roots:
            raise ValueError('duplicate/invalid monster identity')
        seen_codes.add(code); seen_roots.add(asset)
        path = 'public/assets/monsters/'+asset
        if code in registry and registry[code]['assetRoot'] != '/assets/monsters/'+asset:
            raise ValueError('registry assetRoot mismatch: '+code)
        rows.append({'key': 'monster:'+code, 'species': asset, 'stage': 1, 'name': m['displayName'],
                     'assetRoot': path, 'identityStatus': m['productionStatus'],
                     'runtimeRegistered': code in registry, 'movementProfile': m['movementProfile'],
                     'personality': {'behaviorProfile': m['behaviorProfile'], 'visualTheme': m['visualTheme']},
                     'behaviorStatus': 'EXISTING_PARTIAL' if m['productionStatus'] == 'PRODUCTION' else 'BEHAVIOR_APPROVAL_REQUIRED'})
    return rows


def reference_catalog(root):
    catalog = read(root/'design/visual-reference-v1/catalog.json')
    if catalog['runtimeActivation'] is not False:
        raise ValueError('concept activation forbidden')
    for reference in catalog['references'].values():
        path = local_file(root, reference['path'])
        if reference['kind'] != 'CONCEPT_REFERENCE' or reference['productionEligible'] is not False or path is None:
            raise ValueError('invalid concept reference')
        if hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
            raise ValueError('concept source hash mismatch')
    forms = catalog['companionForms']
    if {(r['species'],r['stage']) for r in forms} != {(s,n) for s in ('moa','ruu','nox') for n in range(1,6)} or len(forms) != 15:
        raise ValueError('expected 15 unique companion forms')
    if any(r['runtimeEnabled'] is not False or r['productionNameOverride'] is not None or r['requiredActions'] != list(ACTIONS) for r in forms):
        raise ValueError('companion runtime override forbidden')
    concepts = catalog['monsterConcepts']
    if len(concepts) != 100 or {r['conceptId'] for r in concepts} != {f'M{i:03d}' for i in range(1,101)}:
        raise ValueError('expected M001-M100 exactly once')
    for r in concepts:
        if any(r[k] is not None for k in ('speciesIdentity','existingMonsterCode','assetIdentity','rarity','spawnTier')) or r['runtimeEnabled'] is not False:
            raise ValueError('concept identity/balance cannot become runtime data')
        if r['animationProfile']['requiredActions'] != list(ACTIONS):
            raise ValueError('incomplete action contract')
        if r['skillIdentity']['serverCode'] is not None or r['skillIdentity']['cooldownTurns'] is not None:
            raise ValueError('unapproved skill binding')
    errors = validate_behavior_proposals([dict(species=r['conceptId'], movementProfile=r['movementProfile']['value'],
                                              **{k:r['speciesBehavior'][k] for k in BEHAVIOR_AXES}) for r in concepts])
    if errors:
        raise ValueError('; '.join(errors))
    return catalog


def concept_references(catalog, known_keys):
    if catalog is None:
        return {}
    refs = {}
    for entry in read(catalog):
        if set(entry) != {'key', 'kind', 'path'} or entry['kind'] != 'CONCEPT_REFERENCE':
            raise ValueError('concept catalog requires key/kind=CONCEPT_REFERENCE/path')
        key = entry['key']
        if key not in known_keys or key in refs:
            raise ValueError('unknown/duplicate concept identity: '+key)
        path = local_file(catalog.parent, entry['path'])
        if path is None:
            raise ValueError('missing concept: '+entry['path'])
        refs[key] = {'kind': 'CONCEPT_REFERENCE', 'path': entry['path'],
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'comparison': 'VISUAL_REVIEW_REQUIRED'}
    return refs


def validate_behavior_proposals(rows):
    """Check review proposals only; values never feed the existing native controllers.

    Each axis is an explicit human-authored habit description. Copying one profile's
    habit onto every species is rejected. Numerical tuning remains native-owner review.
    """
    if not isinstance(rows, list) or not rows:
        return ['nonempty behavior proposal list required']
    seen, groups, errors = set(), {}, []
    for row in rows:
        key, profile = row.get('species'), row.get('movementProfile')
        if not isinstance(key, str) or not key or key in seen:
            errors.append('missing/duplicate species'); continue
        seen.add(key)
        if profile not in ('GROUND', 'JUMP', 'FLYING', 'FLOATING', 'STATIC', 'EDGE', 'FREE_2D'):
            errors.append(key+': invalid movement profile'); continue
        signature = []
        for axis in BEHAVIOR_AXES:
            value = row.get(axis)
            if not isinstance(value, str) or not value.strip():
                errors.append(key+': '+axis+' required'); value = ''
            signature.append(' '.join(value.lower().split()))
        for other, prior in groups.setdefault(profile, []):
            for axis, a, b in zip(BEHAVIOR_AXES, signature, prior):
                if a and a == b:
                    errors.append(f'{key}/{other}: identical {axis} within {profile}')
        groups[profile].append((key, signature))
    return errors


def inventory(root=ROOT, catalog=None):
    catalog_data = reference_catalog(root)
    existing = existing_identities(root)
    rows = existing[:15]
    forms = {r['key']:r for r in catalog_data['companionForms']}
    for row in rows:
        row['conceptDesign'] = forms[row['key']]
    for r in catalog_data['monsterConcepts']:
        rows.append({'key':'concept:'+r['conceptId'], 'species':None, 'stage':None, 'name':r['observedForm'],
                     'assetRoot':None, 'identityStatus':'IDENTITY_REVIEW_REQUIRED', 'runtimeRegistered':False,
                     'behaviorStatus':'PROPOSED_REQUIRES_NATIVE_OWNER_REVIEW', 'conceptDesign':r})
    refs = concept_references(catalog, {r['key'] for r in rows})
    requests, owners = [], []
    for row in rows + existing[15:]:
        base = row['assetRoot']
        row['concept'] = refs.get(row['key'], {'status': 'CONCEPT_REFERENCE_ONLY', 'path':row['conceptDesign']['reference']} if 'conceptDesign' in row else {'status':'NO_AUTOMATIC_CONCEPT_MATCH'})
        row['baseStatus'] = 'ASSET_REQUIRED'
        if base:
            path = local_file(root, base+'/base.png')
            if path:
                row['baseSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                row['baseErrors'] = png_errors(path, require_transparency=True, bounds=[])
                row['baseStatus'] = 'INVALID_FRAMES' if row['baseErrors'] else 'EXISTING_BASE_REFERENCE'
            manifest = local_file(root, base+'/manifest.json')
            if manifest:
                requests.append({'species': row['species'], 'stage': row['stage'], 'base': base, 'manifest': read(manifest)})
                owners.append(row)
    for row, result in zip(owners, inspect_frames(root, requests)):
        row['manifestInspection'] = result
    for row in rows + existing[15:]:
        clips = row.get('manifestInspection', {}).get('clips', {})
        row['actions'] = {}
        for action in ACTIONS:
            candidates = {c: clips[c] for c in CANDIDATES.get(action, []) if c in clips}
            valid = [c for c, info in candidates.items() if info['status'] == 'FRAME_FILES_VALID']
            row['actions'][action] = {'status': 'EXISTING_FRAME_REFERENCE' if valid else 'ASSET_REQUIRED',
                                      'existingClipCandidates': candidates,
                                      'plannedClipPath': (str(Path(clips[valid[0]]['frames'][0]).parent)+'/<frame>.png') if valid else (row['assetRoot']+'/{approvedClip}/{approvedPrefix}_NN.png') if row['assetRoot'] else None,
                                      'binding': 'REVIEW_REQUIRED', 'visualApproval': 'NOT_VERIFIED'}
    errors = [r['key']+': invalid manifest/frames' for r in rows+existing[15:] if r.get('baseStatus')=='INVALID_FRAMES' or r.get('manifestInspection',{}).get('status')=='INVALID_MANIFEST' or any(c['status']=='INVALID_FRAMES' for c in r.get('manifestInspection',{}).get('clips',{}).values())]
    return {'errors':errors, 'schemaVersion': 1, 'status': 'PREPARATION_ONLY', 'runtimeActivation': False,
            'scope': {'companions': 15, 'monsters': 100}, 'hooks': HOOKS,
            'pathContract': {'companions': 'public/assets/creatures/{species}/stage{stage:02d}',
                             'monsters': 'public/assets/monsters/{approvedAssetIdentity}',
                             'unassigned': 'IDENTITY_REQUIRED; no directory or code invented'},
            'behaviorContract': {'requiredDistinctAxes': BEHAVIOR_AXES, 'activation': 'HUMAN_REVIEW_REQUIRED',
                                 'owner': HOOKS['behavior'], 'preserve': ['native movement authority', 'existing RNG/timers', 'busy/terminal suppression']},
            'manifestPreparation': {'format':'existing Manifest after delivery, not a new engine',
                                    'canvas':{'width':256,'height':256}, 'anchor':{'x':0.5,'y':1},
                                    'sourceFacing':'RIGHT', 'productionOverwrite':False,
                                    'frameCount':'ARTIST_DELIVERY_REQUIRED', 'frameDuration':'NATIVE_SYNC_REVIEW_REQUIRED',
                                    'naming':'existing frameUrls; firstFrame/filePrefix from approved manifest',
                                    'missingActionPolicy':'ASSET_REQUIRED; own-species base only, never another species'},
            'characters': rows, 'existingMonsterInventory': existing[15:], 'comparison':catalog_data['comparison'], 'withinConceptSimilarityReview':catalog_data['withinConceptSimilarityReview'],
            'summary': {'unassignedMonsterIdentities': sum(r['identityStatus']=='IDENTITY_REVIEW_REQUIRED' for r in rows),
                        'conceptReferences': len(catalog_data['references'])+len(refs),
                        'actionsRequiringAssets': sum(a['status']=='ASSET_REQUIRED' for r in rows for a in r['actions'].values())}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory'); inv.add_argument('--concept-catalog', type=Path)
    frames = sub.add_parser('frames'); frames.add_argument('--manifest', type=Path, required=True)
    frames.add_argument('--species', required=True); frames.add_argument('--stage', type=int, required=True)
    frames.add_argument('--kind', choices=['CONCEPT_REFERENCE', 'SPRITE_CANDIDATE'], default='CONCEPT_REFERENCE')
    behavior = sub.add_parser('behavior'); behavior.add_argument('--proposals', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'inventory':
        result = inventory(catalog=a.concept_catalog.resolve() if a.concept_catalog else None)
    elif a.command == 'behavior':
        errors = validate_behavior_proposals(read(a.proposals))
        result = {'status': 'INVALID_PROPOSAL' if errors else 'REVIEW_REQUIRED', 'errors': errors, 'runtimeActivation': False}
    elif a.kind == 'CONCEPT_REFERENCE':
        result = {'status': 'ASSET_REQUIRED', 'reason': 'Concept references cannot qualify as production sprites', 'runtimeActivation': False}
    else:
        # Keep candidate directory outside public: the tool has no registration/copy operation.
        if not re.fullmatch('[a-z][a-z0-9_]*', a.species) or not 1 <= a.stage <= 5:
            raise ValueError('candidate requires canonical species and stage 1..5')
        path = a.manifest.resolve()
        if path.is_relative_to((ROOT/'public').resolve()):
            raise ValueError('candidate validation must use a separate staging directory')
        manifest = read(path)
        request = {'species': a.species, 'stage': a.stage, 'base': '.', 'manifest': manifest}
        # The TypeScript source is from ROOT; frame paths are relative to a separate staging directory.
        parsed = runtime_manifests(ROOT, [request])[0]
        errors, missing = [], []
        if 'error' in parsed:
            errors.append(parsed['error'])
        elif manifest.get('canvas') != {'width':256,'height':256} or not parsed['clips']:
            errors.append('nonempty 256x256 manifest required')
        else:
            for urls in parsed['clips'].values():
                for relative in urls:
                    frame = local_file(path.parent, relative)
                    if frame is None: missing.append(relative)
                    else: errors.extend(relative+': '+e for e in png_errors(frame, require_transparency=True, bounds=[]))
        result = {'status': 'INVALID_FRAMES' if errors else 'ASSET_REQUIRED' if missing else 'FRAME_FILES_VALID',
                  'errors': errors, 'missing': missing, 'visualApproval': 'NOT_VERIFIED', 'runtimeActivation': False}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get('errors') or result.get('status') in ('INVALID_FRAMES','ASSET_REQUIRED') else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
