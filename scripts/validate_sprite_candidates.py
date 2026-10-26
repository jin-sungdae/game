"""Read-only candidate clip review using the existing #85 PNG and registration checks."""
import argparse
import json
from pathlib import Path
from visual_asset_inventory import clips, candidate


def review(directory, species, stage):
    directory = Path(directory)
    if not (directory/'manifest.json').is_file():
        raise ValueError('candidate manifest required')
    available = clips(directory, (species, stage))
    if not available:
        raise ValueError('at least one clip required')
    results = {}
    for name, clip in available.items():
        frames = clip['frameEvidence']
        reference = Path(frames[0]['file'])
        registration = [candidate(Path(frame['file']), reference) for frame in frames]
        failures = list(clip['errors']) + list(clip['missingOrInvalid'])
        failures += [str(frame['file'])+': '+error
                     for frame, check in zip(frames, registration) for error in check['errors']]
        hashes = {}
        for index, frame in enumerate(frames):
            if frame.get('pixelSha256'):
                hashes.setdefault(frame['pixelSha256'], []).append(index)
        results[name] = {
            'status': 'VALIDATION_FAILED' if failures else 'AUTOMATED_CHECKS_PASS_VISUAL_REVIEW_REQUIRED',
            'errors': failures,
            'reference': str(reference),
            'referenceApproval': 'NOT_ESTABLISHED_BY_THIS_TOOL',
            'frames': [{'file': frame['file'], 'sha256': frame.get('sha256'),
                        'pixelSha256': frame.get('pixelSha256'), 'bounds': frame.get('bounds'),
                        'driftPixels': check['driftPixels'], 'errors': check['errors']}
                       for frame, check in zip(frames, registration)],
            'repeatedPixelGroups': [indices for indices in hashes.values() if len(indices)>1],
        }
    return {'species': species, 'stage': stage, 'clips': results,
            'productionEligible': False, 'runtimeConnected': False,
            'visualIdentity': 'MANUAL_REVIEW_REQUIRED',
            'backgroundResidue': 'MANUAL_REVIEW_REQUIRED',
            'anatomicalContinuity': 'MANUAL_REVIEW_REQUIRED', 'gui': 'DEFERRED_GUI'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--species', required=True)
    parser.add_argument('--stage', type=int, required=True)
    args = parser.parse_args()
    result = review(args.directory, args.species, args.stage)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if any(c['status']=='VALIDATION_FAILED' for c in result['clips'].values()) else 0)
