"""Independent first-attempt quiescence/defeat poses. Never repairs existing clips."""
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path('design/production-batches/luma-asset-16')
spec = importlib.util.spec_from_file_location('previous', ROOT/'continuation-v3/produce.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
p = previous.p
# Sleep has a sustained relaxed middle, a small residual bell pulse, then wake.
relax = [.03,.18,.45,.76,.95,1,.99,.97,.94,.72,.32,0]
quiet = [.03,.3,.65,.85,.81,.79,.84,.8,.77,.56,.2,0]
# Defeat has progressive loss of support, ending in a held droop, not BASE.
sink = [.025,.08,.18,.32,.49,.65,.78,.87,.93,.965,.987,1]
lag = [.015,.04,.1,.21,.37,.54,.7,.82,.9,.95,.98,1]
SPECS = [
 ('M061','SLEEP',[65,52,195,196],350,False,
  'Eyeless quiescence entry/hold/wake study. Oral arms and tentacles relax downward during a prolonged reduced bell pulse. No eyes added. Not an approved biological sleep or Runtime behavior.',[
   p('left-bell-reduced-pulse',91,107,19,19,1.4,.7,quiet),
   p('right-bell-reduced-pulse',174,110,17,23,-1.3,.6,quiet),
   p('oral-arm-relaxation',136,131,22,18,0,1.4,relax),
   p('near-tentacle-resting-droop',108,165,22,26,.8,1.8,relax),
   p('far-tentacle-resting-droop',163,165,20,24,-.7,1.6,relax)]),
 ('M061','DEFEAT',[65,52,195,196],180,False,
  'Progressive local bell sag and delayed oral-arm/tentacle droop. Terminal pose is held, not recovered. No whole-body translation; terminal anatomy needs human review.',[
   p('left-bell-sag',91,107,19,19,.7,1.9,sink),
   p('right-bell-sag',174,110,17,23,-.6,1.7,sink),
   p('oral-arm-loss-of-support',136,131,22,18,0,2.1,lag),
   p('near-tentacle-droop',108,165,22,26,.7,2.2,lag),
   p('far-tentacle-droop',163,165,20,24,-.6,2,lag)]),
 ('M062','DEFEAT',[146,78,201,174],180,False,
  'Muzzle and upper trunk progressively droop and remain lowered. Eyes unchanged; no eyelid synthesis, tail/fin propulsion or failed MOVE data used.',[
   p('muzzle-droop',190,106,10,11,-.5,1.4,sink),
   p('cheek-support-loss',163,106,15,12,-.3,.7,lag),
   p('upper-trunk-slump',168,139,20,23,-.6,1.3,lag)]),
 ('M064','DEFEAT',[82,139,216,196],180,False,
  'Near claw lowers then far claw and soft neck lose support. Shell and ground contact fixed. Held defeated posture; no ATTACK source or recovery reuse.',[
   p('near-claw-lowers',149,175,22,20,-.7,1.8,sink),
   p('far-claw-lowers',199,165,15,24,-.5,1.7,lag),
   p('soft-neck-droop',132,153,12,11,-.4,.9,lag)])
]

def main():
    attempts = []
    for identity, action, rect, duration, loop, meaning, parts in SPECS:
        name = action.lower()
        output = ROOT/identity/(name+'-candidate')
        if output.exists():
            raise RuntimeError(f'Existing candidate protected: {output}')
        output.mkdir(parents=True)
        left, top, right, bottom = rect
        fixed = f'y>={bottom}||y<={top}||x<={left}||x>={right}'
        base = f'design/production-batches/monsters/batch07/{identity}/base-v2.png'
        code = re.sub(r'const root=.*;', f'const root={json.dumps(str(output))};', previous.TEMPLATE)
        code = re.sub(r'const parts=.*;', f'const parts={json.dumps(parts)};', code)
        code = re.sub(r'const fixed=.*;', f'const fixed=(x,y)=>{fixed};', code)
        code = code.replace('design/production-batches/monsters/batch07/M061/base-v2.png', base)
        code = code.replace('/rigged/breath', '/rigged/'+name).replace("'breath_'", repr(name+'_'))
        code = code.replace('frame<8','frame<12').replace('frame<7','frame<11').replace('frame===7','frame===11').replace('size!==8','size!==12')
        if action == 'DEFEAT':
            code = code.replace('with exact BASE terminal frame', 'with held drooped terminal pose')
            code = code.replace('(frame<11&&(!changed||!alphaChanges))||(frame===11&&changed)', '(!changed||!alphaChanges)')
        code = re.sub(r'protectedRegions:"[^"]*"', f'protectedRegions:{json.dumps(fixed)}', code)
        code = code.replace('M061 BREATH', identity+' '+action)
        code = code.replace('(async()=>{', "(async()=>{\n if(fs.existsSync(root+'/rigged'))throw Error('Existing frames protected; no implicit retry');")
        (output/'rig.cjs').write_text(code)
        contract = dict(sessionId='LUMA-ASSET-16',conceptId=identity,species=None,
            status='CANDIDATE_ONLY',runtimeEnabled=False,productionEligible=False,
            sourceBase=base,canvas=dict(width=256,height=256),anchor=dict(x=.5,y=1),
            anchorApproval='NOT_APPROVED',clip=dict(name=action,frames=12,frameDuration=duration,loop=loop),
            movableRect=rect,parts=parts,anatomyScope=meaning,
            artworkReview='HUMAN_REVIEW_REQUIRED',naturalMotion='HUMAN_REVIEW_REQUIRED',
            gui='DEFERRED_GUI',repairIterations=3,repairLimit=3,
            repairScope='Independent first attempt; no failed source reuse or automatic repair',wholeImageTransform=False)
        if action == 'SLEEP':
            contract['terminalFrame'] = dict(index=11,role='EXACT_BASE_RETURN',expectedPixelChanges=0)
        else:
            contract['terminalPose'] = dict(role='HELD_DEFEAT',recoveryApproved=False,
                baseReturn='NOT_APPLICABLE; separate approved recovery required')
        (output/'candidate-clip.json').write_text(json.dumps(contract,indent=2)+'\n')
        result = subprocess.run(['node',str(output/'rig.cjs')],env=os.environ.copy(),capture_output=True,text=True)
        attempts.append(dict(conceptId=identity,action=action,exitCode=result.returncode,stderr=result.stderr,path=str(output)))
        print(identity,action,result.returncode,flush=True)
    (ROOT/'continuation-v4/generation.json').write_text(json.dumps(attempts,indent=2)+'\n')

if __name__ == '__main__':
    main()
