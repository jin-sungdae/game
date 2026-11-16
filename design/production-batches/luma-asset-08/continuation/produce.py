"""최초 독립 LOOK/RECOVERY 후보. 기존 실패/완료 후보 덮어쓰기 없음."""
import copy,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'design/production-batches/luma-asset-08'
EYES={'M021':[(177,136,7,9,.85)],'M022':[(198,116,4.5,5,.7)],'M024':[(154,106,9,12,.9),(182,114,4.5,7,.6)],'M025':[(166,117,7,8,.8),(191,125,3,5,.5)]}
template=(ROOT/'design/production-batches/action-followup/M010/rig-look.cjs').read_text()
ledger=json.loads((ROOT/'design/creature-production-queue.json').read_text())
for code,eyes in EYES.items():
    row=next(r for r in ledger['creatures'] if r['creatureId']==code)
    folder=OUT/code/'look';folder.mkdir(parents=True,exist_ok=False)
    spec=json.loads((ROOT/'design/production-batches/action-followup/M010/candidate-clip.json').read_text())
    spec.update(conceptId=code,sourceBase=row['basePath'],eyes=[dict(zip(['x','y','rx','ry','dx'],e)) for e in eyes],sessionId='LUMA-ASSET-08',repairIterations=3)
    spec['clip'].update(loop=False,frameDuration=180)
    spec['anatomyScope']='기존 안구 내부 국소 시선 이동. Alpha·외곽·머리·귀·몸통·발 고정. 새 눈꺼풀/머리 회전 생성 아님.'
    spec['timingScope']='독립 one-shot 시선 후보. 외형·정체성·자연스러움은 승인 대기.'
    (folder/'candidate-clip.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    text=template.replace('design/production-batches/action-followup/M010',folder.relative_to(ROOT).as_posix()).replace('design/production-batches/monsters/batch01/M010/base-v2.png',row['basePath'])
    text=re.sub(r'const eyes=.*?,gaze=', 'const eyes='+json.dumps(spec['eyes'])+',gaze=',text)
    text=text.replace('[0.06, 0.48, 1, 0.6, -0.12, -0.54, -0.9, -0.32]','[0.03, 0.4, 1, 0.55, -0.15, -0.65, -0.3, -0.03]')
    (folder/'rig-look.cjs').write_text(text)
    result=subprocess.run(['node',str(folder/'rig-look.cjs')],cwd=ROOT,capture_output=True,text=True)
    (folder/'execution.json').write_text(json.dumps(dict(exitCode=result.returncode,stderr=result.stderr,retryAllowed=False),indent=2)+'\n')
    print(code,'LOOK',result.returncode)
for code in ['M022','M023','M024','M025']:
    source=BASE/code/('interact' if code=='M024' else 'hit')
    spec=json.loads((source/'candidate-clip.json').read_text());folder=OUT/code/'recovery';folder.mkdir(parents=True,exist_ok=False)
    old=spec['clip']['name'].lower();text=(source/f'rig-{old}.cjs').read_text()
    for i,p in enumerate(spec['parts']): p['samples']=[1,.83,.59,.36,.18,.08,.03,.01] if i==0 else [.87,1,.77,.48,.25,.11,.04,.015]
    spec['clip']=dict(name='RECOVERY',frames=8,frameDuration=130,loop=False)
    spec['anatomyScope']='검증된 국소 파트가 최대 굴곡에서 BASE로 감쇠 복귀. 얼굴·발 고정. 전투 회복 효과나 상태 변경 없음.'
    spec['timingScope']='추가 포즈 없이 기존 국소 변형을 풀어주는 독립 RECOVERY 후보. BASE 복귀 오차 별도 측정.'
    (folder/'candidate-clip.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    text=text.replace(source.relative_to(ROOT).as_posix(),folder.relative_to(ROOT).as_posix()).replace(old,'recovery')
    text=re.sub(r'const parts=.*?;', 'const parts='+json.dumps(spec['parts'],ensure_ascii=False)+';',text,count=1)
    (folder/'rig-recovery.cjs').write_text(text)
    result=subprocess.run(['node',str(folder/'rig-recovery.cjs')],cwd=ROOT,capture_output=True,text=True)
    (folder/'execution.json').write_text(json.dumps(dict(exitCode=result.returncode,stderr=result.stderr,retryAllowed=False),indent=2)+'\n')
    print(code,'RECOVERY',result.returncode)
