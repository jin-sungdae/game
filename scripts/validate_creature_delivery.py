"""Read-only candidate handoff audit. Uses the existing Production PNG decoder.
A valid PNG never establishes species identity, an approved anchor or a complete clip.
"""
import argparse
import hashlib
import json
from pathlib import Path
from visual_asset_inventory import inspect_png

IDENTITIES = {f'{s}_S{i}' for s in ('MOA','RUU','NOX') for i in range(1,6)} | {f'M{i:03}' for i in range(1,101)}

def audit(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'manifest.json').read_text())
    seen, paths, results, errors, hashes = set(), set(), [], [], {}
    for entry in manifest['files']:
        identity, relative = entry['identity'], entry['path']
        path = (directory/relative).resolve()
        if path == directory or directory not in path.parents or path.suffix.lower() != '.png':
            raise ValueError('candidate path must be a PNG inside delivery directory')
        if identity in seen or identity not in IDENTITIES:
            errors.append(f'duplicate or unknown identity: {identity}')
        expected = (f'companions/{identity[:3].lower()}/stage_{identity[-1]}/base.png'
                    if identity in IDENTITIES and '_S' in identity else f'monsters/{identity}.png')
        if relative != expected:
            errors.append(f'identity/path mismatch: {identity}')
        if relative in paths:
            errors.append(f'duplicate path: {relative}')
        seen.add(identity);paths.add(relative)
        check = inspect_png(path)
        if check.get('sha256') != entry.get('sha256'):
            check['errors'].append('handoff SHA-256 mismatch')
        if check['errors']:
            errors.append(f'{identity}: '+', '.join(check['errors']))
        if check.get('pixelSha256'):
            hashes.setdefault(check['pixelSha256'], []).append(identity)
        results.append({'identity':identity,'file':relative,'pngErrors':check['errors'],
            'sha256':check.get('sha256'),'pixelSha256':check.get('pixelSha256'),'alphaBounds':check.get('bounds'),
            'identityReview':'MANUAL_REQUIRED','anchorReview':'MANUAL_REQUIRED',
            'runtimeIdentity':None,'animation':'ASSET_REQUIRED','productionEligible':False})
    missing = sorted(IDENTITIES-seen)
    if missing: errors.append('missing identities: '+', '.join(missing))
    duplicates = [ids for ids in hashes.values() if len(ids)>1]
    if duplicates: errors.append('duplicate decoded pixels across identities')
    return {'status':'VALIDATION_FAILED' if errors else 'PNG_FORMAT_VERIFIED_IDENTITY_UNAPPROVED',
        'manifestSha256':hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest(),
        'expectedIdentities':115,'files':results,'missingIdentities':missing,'duplicatePixelGroups':duplicates,
        'errors':errors,'productionAcceptedPngs':0,'productionAcceptedClips':0,'gui':'DEFERRED_GUI'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    result=audit(p.parse_args().directory);print(json.dumps(result,indent=2))
    raise SystemExit(1 if result['errors'] else 0)
