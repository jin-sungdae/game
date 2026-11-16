"""Build only session review data; validate timing edges without changing source PNGs."""
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
BATCH = ROOT/'design/production-batches/luma-asset-16'
HERE = Path(__file__).resolve().parent
TARGETS = [('M061','SLEEP'),('M061','DEFEAT'),('M062','DEFEAT'),('M064','DEFEAT'),
           ('M061','ATTACK'),('M062','ATTACK'),('M061','MOVE')]

def main():
    previous = json.loads((BATCH/'continuation-v4/validation.json').read_text())
    clips = []
    audits = []
    for monster, action in TARGETS:
        path = BATCH/monster/(action.lower()+'-candidate')
        contract = json.loads((path/'candidate-clip.json').read_text())
        evidence = next(c for c in previous['clips'] if c['conceptId']==monster and c['action']==action)
        if evidence['automated'] != 'PASS':
            raise ValueError('Failed candidates cannot enter playable review')
        files = sorted((path/'rigged'/action.lower()).glob('*.png'))
        data = [Image.open(p).convert('RGBA').tobytes() for p in files]
        rig = json.loads((path/'rig-evidence.json').read_text())
        if len(data)!=12 or any(hashlib.sha256(pixels).hexdigest()!=r['pixelSha256'] for pixels,r in zip(data,rig['frames'])):
            raise ValueError('Original pixels changed')
        definition = json.loads(subprocess.check_output(['node','--input-type=module','-e',
            "import {recipe} from './playback.mjs'; console.log(JSON.stringify(recipe(process.argv[1],process.argv[2])))",monster,action],cwd=HERE,text=True))
        edges=set()
        for phase in definition['phases'].values():
            sequence=[f['frame'] for f in phase['frames']]
            if any(not isinstance(f['ms'],int) or f['ms']<=0 for f in phase['frames']): raise ValueError('Invalid duration')
            edges.update(zip(sequence,sequence[1:]))
            for target in [phase['next'],phase.get('wake')]:
                if target: edges.add((sequence[-1],definition['phases'][target]['frames'][0]['frame']))
        metrics=[]
        for a,b in sorted(edges):
            mean=sum(abs(x-y) for x,y in zip(data[a],data[b]))/len(data[a])
            if mean>2: raise ValueError(f'Continuity failure {monster} {action}: {a}->{b} {mean}')
            metrics.append(dict(source=a,target=b,meanAbsoluteChannelDelta=mean))
        clips.append(dict(id=f'{monster} {action}',monster=monster,action=action,base=contract['sourceBase'],
            files=[str(p.relative_to(ROOT)) for p in files],frameDuration=contract['clip']['frameDuration'],loop=contract['clip']['loop']))
        audits.append(dict(id=f'{monster} {action}',status='PASS',sourceHashesUnchanged=True,edges=metrics))
    (HERE/'review-data.json').write_text(json.dumps(dict(productionApproved=False,runtimeConnected=False,clips=clips),indent=2)+'\n')
    (HERE/'timing-validation.json').write_text(json.dumps(dict(status='PASS',threshold=2,clips=audits,naturalMotion='HUMAN_REVIEW_REQUIRED'),indent=2)+'\n')
    print('7 timing recipes; unchanged source pixels; all phase/loop/wake edges PASS')

if __name__=='__main__': main()
