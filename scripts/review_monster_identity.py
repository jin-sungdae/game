"""Read-only identity evidence: exact pixels are a signal, never a species mapping."""
from pathlib import Path
import hashlib
import json
import sys
import validate_assets

ROOT = Path(__file__).resolve().parents[1]

def asset(path):
    file = ROOT / path
    if not file.is_file():
        return {'path': path, 'status': 'ASSET_REQUIRED'}
    errors, digests = [], []
    errors = validate_assets.png_errors(file, True, [], digests)
    return {'path': path, 'status': 'PNG_INVALID' if errors else 'PNG_FORMAT_VALID',
            'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'pixelHash': digests[0] if digests else None, 'errors': errors}

def review():
    dex = json.loads((ROOT / 'src/entities/monster-dex.json').read_text())
    registry = json.loads((ROOT / 'src/entities/monsters.json').read_text())
    queue = json.loads((ROOT / 'design/creature-production-queue.json').read_text())
    legacy = []
    for row in dex:
        path = registry.get(row['monsterCode'], {}).get('baseAsset')
        legacy.append({'species': row['monsterCode'], 'productionStatus': row['productionStatus'],
                       'archetype': row['archetype'], 'asset': asset('public' + path) if path else {'status': 'ASSET_REQUIRED'}})
    candidates = []
    for row in queue['creatures']:
        code = row['creatureId']
        if not code.startswith('M'):
            continue
        number = int(code[1:])
        folder = ROOT / f'design/production-batches/monsters/batch{(number-1)//10+1:02}' / code
        # Ledger-selected recovery wins. Otherwise inspect the latest preserved normalized base.
        selected = ROOT / row['basePath'] if row.get('basePath') else next((folder/name for name in ['base-v4.png','base-v3.png','base-v2.png','base-v1.png'] if (folder/name).is_file()), folder/'base-v1.png')
        evidence = asset(str(selected.relative_to(ROOT)))
        matches = [old['species'] for old in legacy if evidence.get('pixelHash') and old['asset'].get('pixelHash') == evidence['pixelHash']]
        candidates.append({'conceptId': code, 'asset': evidence, 'exactLegacyPixelMatches': matches,
                           'productionSpeciesId': None, 'mappingApproved': False,
                           'artworkStatus': row['baseStatus'], 'existingBlockReason': row['blockReason'],
                           'identityStatus': 'HUMAN_REVIEW_REQUIRED', 'runtimeEnabled': False})
    return {'schemaVersion': 1, 'interpretation': 'Different hashes do not prove distinct design. Missing legacy art prevents full visual comparison.',
            'legacy': legacy, 'candidates': candidates, 'productionMappingsApproved': 0,
            'missingLegacyArtwork': [x['species'] for x in legacy if x['asset']['status']=='ASSET_REQUIRED']}

if __name__ == '__main__':
    # Caller explicitly chooses where to preserve this evidence; no source mutation.
    result = json.dumps(review(), indent=2) + '\n'
    if len(sys.argv)==2:
        Path(sys.argv[1]).write_text(result)
    else:
        print(result, end='')
