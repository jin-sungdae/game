"""New action candidates only; refuses overwrite. Reuses existing RGBA part sampler."""
import json
import os
import re
import subprocess
from pathlib import Path

ROOT=Path('design/production-batches/luma-asset-16')
TEMPLATE=(ROOT/'M061/breath-candidate/rig.cjs').read_text()
# Distinct anticipation, stroke, trailing and settle phases; no global transform.
pulse=[.03,.18,.45,.8,1,.81,.52,.25,.12,.06,.02,0]
trail=[.02,.05,.12,.3,.61,.9,1,.75,.44,.18,.05,0]
strike=[.02,-.18,-.42,-.6,-.25,.45,1,.72,.38,.15,.04,0]
brace=[.01,.08,.28,.55,.87,1,.7,.45,.24,.1,.03,0]
celebrate=[.03,.25,.65,1,.72,.32,.6,.95,.7,.33,.08,0]
answer=[.02,.08,.3,.65,.96,.72,.4,.66,1,.56,.13,0]
fin=[.02,.5,1,.4,-.5,-1,-.4,.5,.9,.4,.08,0]
fin_lag=[.01,.1,.4,1,.5,-.4,-1,-.5,.3,.8,.22,0]
def p(name,x,y,rx,ry,dx,dy,s):return dict(name=name,x=x,y=y,rx=rx,ry=ry,dx=dx,dy=dy,samples=s)
SPECS=[
('M061','MOVE',[65,52,195,196],115,True,'In-place propulsion study: bell rim contracts then oral arms and middle tentacles trail. No canvas translation. Direction/speed and locomotion suitability remain unapproved.',[
p('left-bell-propulsion',91,107,19,19,2.8,-2.1,pulse),p('right-bell-propulsion',174,110,17,23,-2.6,-1.9,pulse),p('oral-arm-trailing-stroke',136,131,22,18,0,1.8,trail),p('near-tentacle-trail',108,165,22,26,-1.5,1.7,trail),p('far-tentacle-trail',163,165,20,24,1.3,1.6,trail)]),
('M061','ATTACK',[65,122,195,196],95,False,'Tentacle strike study: draw middle sections inward, extend with delayed opposite arm brace, then settle exactly to BASE. No contact/damage/skill semantics activated.',[
p('near-tentacle-draw-strike',108,165,22,26,-3.2,1.6,strike),p('far-tentacle-counterbrace',163,165,20,24,2.1,-1.5,brace),p('oral-arm-anticipation',136,140,15,17,0,-1.2,brace)]),
('M061','VICTORY',[65,122,195,196],130,False,'Two staggered outward tentacle flourishes with oral-arm release. Bell and extreme tips fixed; proposed celebration, not Production-approved expression.',[
p('near-tentacle-flourish',108,165,22,26,-2.8,-2.1,celebrate),p('far-tentacle-answer-flourish',163,165,20,24,2.6,-1.7,answer),p('oral-arm-release',136,143,15,18,0,1.1,answer)]),
('M062','MOVE',[72,112,196,225],90,True,'In-place seahorse propulsion study: opposite-phase dorsal/side fin strokes with delayed curled-tail counterbalance. No whole-image translation or claim of validated trajectory.',[
p('dorsal-fin-stroke',112,154,24,28,-1.5,-1.9,fin),p('side-fin-counterstroke',188,150,8,21,1.2,1.5,fin_lag),p('tail-propulsion-balance',140,197,28,24,-.8,.7,trail)]),
('M062','ATTACK',[146,78,201,174],100,False,'Muzzle thrust anticipation/release with upper-trunk counterbrace; crown and lower tail protected. Physical pose study only, no projectile, contact or damage invented.',[
p('muzzle-draw-thrust',190,106,10,11,1.5,-.8,strike),p('cheek-anticipation',163,106,15,12,-.7,.5,brace),p('upper-trunk-brace',168,139,20,23,-.8,.7,brace)]),
('M062','VICTORY',[127,111,197,221],130,False,'Upper trunk lifts locally while side fin and curled tail answer in two beats. Face/crown stay fixed; distinct celebration candidate, not a relabeled interaction.',[
p('upper-trunk-proud-lift',168,139,20,23,.8,-1.1,celebrate),p('side-fin-salute',188,150,8,21,1.1,-1.2,answer),p('curled-tail-flourish',140,197,25,21,1.1,-1.2,answer)]),
('M064','VICTORY',[82,139,216,196],145,False,'Crab claw salute: near claw lifts first, far claw answers twice, soft neck settles. Shell, eyes, antenna tips and ground contact remain fixed.',[
p('near-claw-salute',149,175,22,20,1.6,-2.6,celebrate),p('far-claw-salute',199,165,15,24,-1.5,-2.3,answer),p('soft-neck-settle',132,153,12,11,-.5,.6,trail)]),
('M064','CHARGE',[82,139,216,196],140,False,'Stationary physical bracing study: claws draw toward the soft abdomen, hold tension, then release to BASE. Not a lunge or attack recovery; no failed ATTACK source or skill effect used.',[
p('near-claw-draw-in',149,175,22,20,-1.7,-1.4,brace),p('far-claw-draw-in',199,165,15,24,-1.8,1.1,brace),p('soft-neck-tension',132,153,12,11,.6,-.7,pulse),p('abdomen-counterbrace',164,169,9,13,-.5,.6,trail)])]

def main():
    attempts=[]
    for identity,action,rect,duration,loop,meaning,parts in SPECS:
        name=action.lower();output=ROOT/identity/(name+'-candidate')
        if output.exists():raise RuntimeError(f'Existing candidate protected: {output}')
        output.mkdir(parents=True)
        left,top,right,bottom=rect;fixed=f'y>={bottom}||y<={top}||x<={left}||x>={right}'
        base=f'design/production-batches/monsters/batch07/{identity}/base-v2.png'
        code=re.sub(r'const root=.*;',f'const root={json.dumps(str(output))};',TEMPLATE)
        code=re.sub(r'const parts=.*;',f'const parts={json.dumps(parts)};',code)
        code=re.sub(r'const fixed=.*;',f'const fixed=(x,y)=>{fixed};',code)
        code=code.replace('design/production-batches/monsters/batch07/M061/base-v2.png',base)
        code=code.replace('/rigged/breath','/rigged/'+name).replace("'breath_'",repr(name+'_'))
        code=code.replace('frame<8','frame<12').replace('frame<7','frame<11').replace('frame===7','frame===11').replace('size!==8','size!==12')
        code=re.sub(r'protectedRegions:"[^"]*"',f'protectedRegions:{json.dumps(fixed)}',code)
        code=code.replace('M061 BREATH',identity+' '+action)
        # Individual rig entrypoint must also refuse to overwrite existing output.
        code=code.replace('(async()=>{',"(async()=>{\n if(fs.existsSync(root+'/rigged'))throw Error('Existing frames protected; no implicit retry');")
        (output/'rig.cjs').write_text(code)
        contract={'sessionId':'LUMA-ASSET-16','conceptId':identity,'species':None,'status':'CANDIDATE_ONLY','runtimeEnabled':False,'productionEligible':False,'sourceBase':base,'canvas':{'width':256,'height':256},'anchor':{'x':.5,'y':1},'anchorApproval':'NOT_APPROVED','clip':{'name':action,'frames':12,'frameDuration':duration,'loop':loop},'movableRect':rect,'parts':parts,'anatomyScope':meaning,'terminalFrame':{'index':11,'role':'EXACT_BASE_RETURN','expectedPixelChanges':0},'artworkReview':'HUMAN_REVIEW_REQUIRED','naturalMotion':'HUMAN_REVIEW_REQUIRED','gui':'DEFERRED_GUI','repairIterations':3,'repairLimit':3,'repairScope':'Independent first attempt only; no failed source reuse, counter reset or automatic repair','wholeImageTransform':False}
        (output/'candidate-clip.json').write_text(json.dumps(contract,indent=2)+'\n')
        result=subprocess.run(['node',str(output/'rig.cjs')],env=os.environ.copy(),capture_output=True,text=True)
        attempts.append({'conceptId':identity,'action':action,'exitCode':result.returncode,'stderr':result.stderr,'path':str(output)})
        print(identity,action,result.returncode,flush=True)
    (ROOT/'continuation-v3/generation.json').write_text(json.dumps(attempts,indent=2)+'\n')

if __name__=='__main__':main()
