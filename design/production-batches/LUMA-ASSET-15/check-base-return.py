"""Additional read-only candidate check. Never rewrites existing measurements.
Numerical continuity does not establish anatomy, natural motion or approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def measure(spec_path):
    spec = json.loads(spec_path.read_text())
    base = np.array(Image.open(ROOT/spec['sourceBase']).convert('RGBA'), dtype=np.int16)
    action = spec['clip']['name'].lower()
    files = sorted((spec_path.parent/'rigged'/action).glob('*.png'))
    if len(files) != spec['clip']['frames']:
        return {'conceptId':spec['conceptId'], 'action':action.upper(), 'status':'INCOMPLETE', 'errors':['FRAME_COUNT_MISMATCH']}
    first, last = [np.array(Image.open(p).convert('RGBA'), dtype=np.int16) for p in (files[0],files[-1])]
    start = float(np.abs(first-base).mean()); end = float(np.abs(last-base).mean())
    seam = float(np.abs(first-last).mean())
    # REST is a pose entry, not a promised return-to-base one-shot.
    returns = action not in ('rest', 'sleep', 'defeat')
    errors = ['BASE_RETURN_DELTA'] if returns and end > .1 else []
    if spec['clip']['loop'] and seam > .1: errors.append('LOOP_SEAM_DELTA')
    return {'conceptId':spec['conceptId'],'action':action.upper(),'status':'FAIL' if errors else 'PASS',
            'sourceSha256':hashlib.sha256((ROOT/spec['sourceBase']).read_bytes()).hexdigest(),
            'startMeanRgbaDelta':start,'endMeanRgbaDelta':end,'seamMeanRgbaDelta':seam,
            'baseReturnRequired':returns,'maxMeanRgbaDelta':.1,'errors':errors,
            'scope':'Numerical endpoint only; existing stricter per-frame and visual failures remain blocking',
            'productionEligible':False,'runtimeConnected':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise SystemExit('Evidence output already exists; preserve prior run')
    rows=[measure(spec) for spec in sorted(HERE.glob('M*/*/candidate-clip.json'))]
    args.output.write_text(json.dumps({'checks':rows,'manualReview':'HUMAN_REVIEW_REQUIRED'},indent=2)+'\n')
    print(json.dumps({status:sum(r['status']==status for r in rows) for status in ['PASS','FAIL','INCOMPLETE']}))
