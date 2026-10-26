"""LUMA-ASSET-08: 기존 오프라인 Part Rig를 재사용하는 최초 후보 제작. 재실행 덮어쓰기 금지."""
import copy
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'design/production-batches/action-followup'
TEMPLATE = (SOURCE / 'M022/interact-pilot/rig-interact.cjs').read_text()
CONFIG = {
    'M021': ('M022/interact-pilot', [60, 142, 185, 216], [
        {'name':'작은-꼬리', 'x':82,'y':166,'rx':18,'ry':19,'dx':1.0,'dy':-1.2},
        {'name':'어깨', 'x':132,'y':187,'rx':18,'ry':16,'dx':-.8,'dy':-.5}]),
    'M022': ('M022/interact-pilot', None, None),
    'M023': ('M023/interact-pilot', None, None),
    'M024': ('M024/hit-pilot', None, None),
    'M025': ('M022/interact-pilot', [47, 128, 194, 210], [
        {'name':'말린-꼬리-하부', 'x':81,'y':178,'rx':24,'ry':23,'dx':1.1,'dy':-.9},
        {'name':'가슴', 'x':158,'y':176,'rx':20,'ry':25,'dx':-.6,'dy':-.7}]),
}
TIMING = {
    'CURSOR_REACT': ([.02,.18,.65,1,.83,.48,.20,.04], [.01,.04,.18,.49,.91,1,.57,.06], 125),
    'HIT': ([.03,.75,1,.68,.39,.21,.08,.02], [.02,.18,.65,1,.75,.46,.19,.04], 100),
    'INTERACT': ([.02,.08,.28,.66,1,.79,.42,.05], [.01,.03,.10,.30,.68,1,.62,.07], 150),
}
queue = json.loads((ROOT/'design/creature-production-queue.json').read_text())
for code, (source, rect, parts) in CONFIG.items():
    prior = json.loads((SOURCE/source/'candidate-clip.json').read_text())
    row = next(r for r in queue['creatures'] if r['creatureId']==code)
    for action, (lead, follow, duration) in TIMING.items():
        old = next(a for a in row['actions'] if a['action']==action)
        if old['animationStatus'] != 'ASSET_REQUIRED': continue
        folder = OUT/code/action.lower()
        if folder.exists(): continue  # 기존 후보/실패를 덮어쓰거나 재시도하지 않음
        folder.mkdir(parents=True, exist_ok=False)
        spec = copy.deepcopy(prior)
        spec.update(conceptId=code, sourceBase=row['basePath'], movableRect=rect or prior['movableRect'],
                    sessionId='LUMA-ASSET-08', repairIterations=3, productionEligible=False,
                    runtimeEnabled=False, sourceRig=f'design/production-batches/action-followup/{source}',
                    sourceFacing='FRONT' if code=='M023' else 'RIGHT')
        spec['clip'] = dict(name=action,frames=8,frameDuration=duration,loop=False)
        spec['parts'] = copy.deepcopy(parts or prior['parts'])
        for i, part in enumerate(spec['parts']):
            part['samples'] = lead if i==0 else follow
            if action=='HIT': part['dx']=-abs(part['dx'])*1.15; part['dy']=abs(part['dy'])*.8
            elif action=='CURSOR_REACT': part['dx']*=.65; part['dy']*=.7
        spec['anatomyScope']='기존 BASE의 국소 파트만 변형. 얼굴·발·외곽 극점 보호. M023은 코어 고정, 하부 장갑만 반응. 이동·회전·신규 포즈를 주장하지 않음.'
        spec['behaviorContract']='승인되지 않은 Species/Personality/MovementProfile/SpeciesBehavior는 NOT_VERIFIED 유지. 정지 반응 후보이며 runtime 정책 없음.'
        spec['timingScope']='피격은 빠른 압축과 회복, 상호작용은 느린 반응, 커서 반응은 낮은 진폭의 주의 반응. one-shot 후보.'
        (folder/'candidate-clip.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
        text = TEMPLATE
        text = re.sub(r'const root=.*?;', 'const root='+json.dumps(folder.relative_to(ROOT).as_posix())+';',text,count=1)
        text = re.sub(r'const parts=.*?;', 'const parts='+json.dumps(spec['parts'],ensure_ascii=False)+';',text,count=1)
        l,t,r,b=spec['movableRect']; fixed=f'y>={b}||y<={t}||x<={l}||x>={r}'
        text=re.sub(r'const fixed=.*?;',f'const fixed=(x,y)=>{fixed};',text,count=1)
        text=text.replace('design/production-batches/monsters/batch03/M022/base-v2.png',spec['sourceBase'])
        text=text.replace('interact',action.lower()).replace('M022 INTERACT',f'{code} {action}')
        text=text.replace('y>=198||y<=92||x<=27||x>=219',fixed)
        text=text.replace('PR #114 independent first attempt; no failure recovery','LUMA-ASSET-08 independent first attempt; existing repair ceiling remains 3/3; no failure recovery')
        (folder/f'rig-{action.lower()}.cjs').write_text(text)
        result = subprocess.run(['node',str(folder/f'rig-{action.lower()}.cjs')],cwd=ROOT, capture_output=True, text=True)
        (folder/'execution.json').write_text(json.dumps(dict(exitCode=result.returncode,stdout=result.stdout,stderr=result.stderr,repairIterations=3,retryAllowed=False),indent=2)+'\n')
        print(code, action, result.returncode)
