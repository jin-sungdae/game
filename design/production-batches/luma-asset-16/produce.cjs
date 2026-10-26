// LUMA-ASSET-16: offline candidate authoring only.
// Inverse sampler reused verbatim from M061/interact-pilot/rig-interact.cjs.
// No generated artwork, global transform, registry write or runtime activation.
const fs = require('fs');
const path = require('path');
const {execFileSync} = require('child_process');
const root = 'design/production-batches/luma-asset-16';
const template = fs.readFileSync('design/production-batches/action-followup/M061/interact-pilot/rig-interact.cjs', 'utf8');
const idleA = [0.08,0.32,0.68,1,0.78,0.46,0.19,0.04];
const idleB = [0.55,0.84,1,0.72,0.38,0.1,0.03,0.24];
const settleA = [1,0.82,0.59,0.38,0.22,0.11,0.045,0.01];
const settleB = [0.42,0.72,1,0.78,0.49,0.25,0.09,0.02];
const noticeA = [0.01,0.12,0.46,0.82,1,0.91,0.38,0.03];
const noticeB = [0.02,0.04,0.12,0.34,0.78,1,0.61,0.05];
const hitA = [0.01,1,0.72,0.42,0.22,0.11,0.05,0.02];
const hitB = [0.02,0.09,0.38,0.86,1,0.58,0.23,0.04];
const greetA = [0.02,0.34,0.9,0.54,1,0.62,0.24,0.04];
const greetB = [0.01,0.08,0.28,0.76,0.48,1,0.52,0.03];
function part(name,x,y,rx,ry,dx,dy,samples) {return {name,x,y,rx,ry,dx,dy,samples};}
const species = {
 M061: {rect:[65,122,195,196], anatomy:'Blue jellyfish: preserve bell, face and extreme tentacle tips; deform two middle tentacle sections independently. Gentle FLOATING proposal only.',
  clips: {
   IDLE:[200,true,'Small opposite tentacle undulations, delayed far-side curl; no whole-body bob.',[part('near-tentacle-undulation',108,165,22,26,1.8,-0.7,idleA),part('far-tentacle-counterwave',163,165,20,24,-1.4,0.8,idleB)]],
   REST:[180,false,'Near tentacle relaxes downward while far tentacle releases after a delay; transition to base rest, not sleep.',[part('near-tentacle-release',108,165,22,26,1.1,-1.5,settleA),part('far-tentacle-release',163,165,20,24,-0.8,-1.1,settleB)]],
   CURSOR_REACT:[140,false,'Unilateral attention curl held before release; far tentacle counterbalances without chasing cursor.',[part('near-tentacle-attention',108,165,22,26,-2.1,-1.2,noticeA),part('far-tentacle-balance',163,165,20,24,0.6,0.5,noticeB)]],
   HIT:[100,false,'Two tentacles recoil inward at different phases; bell remains registered.',[part('near-tentacle-recoil',108,165,22,26,2.2,-1.8,hitA),part('far-tentacle-brace',163,165,20,24,-2,-1.3,hitB)]]
  }},
 M062: {rect:[70,112,196,225], anatomy:'Coral seahorse: preserve head, coral crown and tail endpoint; reuse thorax and curled-tail rig. Curious FLOATING proposal only.',
  clips: {
   IDLE:[180,true,'Thorax sways locally while curled tail counters out of phase; fixed face and crown.',[part('thorax-resting-sway',162,145,23,27,0.8,-0.6,idleA),part('tail-countercurl',140,197,28,24,-1.2,0.9,idleB)]],
   REST:[170,false,'Unwind thorax tension followed by delayed tail settling, returning to resting base.',[part('thorax-release',162,145,23,27,1.2,-0.8,settleA),part('tail-settle',140,197,28,24,-1.4,-0.6,settleB)]],
   CURSOR_REACT:[130,false,'Brief thorax orientation toward the stimulus with tail counterbrace; no displacement or gaze claim.',[part('thorax-notice',162,145,23,27,1.5,-0.9,noticeA),part('tail-attention-brace',140,197,28,24,-0.9,1.2,noticeB)]],
   INTERACT:[125,false,'Two local acknowledgement beats: thorax response then a stronger curled-tail answer.',[part('thorax-acknowledge',162,145,23,27,1.2,0.8,greetA),part('tail-answer',140,197,28,24,1.9,-1.3,greetB)]]
  }},
 M064: {rect:[82,139,216,196], anatomy:'Purple shelled crab: rigid shell, eyes, antennae and ground contact protected. Adapt existing inverse sampler to separate near/far claw weights; patient GROUND proposal only. Never uses failed ATTACK source.',
  clips: {
   IDLE:[220,true,'Small independent claw articulation with delayed far claw, shell and stance fixed.',[part('near-claw-flex',149,175,22,20,1,-0.8,idleA),part('far-claw-flex',199,165,15,24,-0.8,-0.6,idleB)]],
   REST:[190,false,'Relax raised claw tension in sequence; keep feet and heavy shell stationary.',[part('near-claw-lower',149,175,22,20,0.7,-1.4,settleA),part('far-claw-lower',199,165,15,24,-0.5,-1.1,settleB)]],
   CURSOR_REACT:[170,false,'Patient single near-claw lift and hold with small far-claw counterbalance.',[part('near-claw-notice',149,175,22,20,-1.1,-1.7,noticeA),part('far-claw-balance',199,165,15,24,0.4,0.6,noticeB)]],
   INTERACT:[160,false,'Two small greeting claw lifts, far claw answers after near claw; no attack lunge.',[part('near-claw-greeting',149,175,22,20,1.5,-1.8,greetA),part('far-claw-answer',199,165,15,24,-1.1,-1.4,greetB)]],
   HIT:[110,false,'Quick near-claw tuck followed by delayed far-claw brace; no shell deformation.',[part('near-claw-tuck',149,175,22,20,-1.7,0.9,hitA),part('far-claw-brace',199,165,15,24,-1.3,1.1,hitB)]]
  }}
};
for (const [id, spec] of Object.entries(species)) for (const [action, [duration, loop, motion, parts]] of Object.entries(spec.clips)) {
 const name = action.toLowerCase(), output = `${root}/${id}/${name}-candidate`;
 if (fs.existsSync(output)) throw Error('Candidate exists; never overwrite or silently retry: '+output);
 fs.mkdirSync(output,{recursive:true});
 const [left,top,right,bottom] = spec.rect;
 const fixed = `y>=${bottom}||y<=${top}||x<=${left}||x>=${right}`;
 const sourceBase = `design/production-batches/monsters/batch07/${id}/base-v2.png`;
 let code = template.replace(/const root=.*;/,`const root=${JSON.stringify(output)};`)
  .replace(/const parts=.*;/,`const parts=${JSON.stringify(parts)};`)
  .replace(/const fixed=.*;/,`const fixed=(x,y)=>${fixed};`)
  .replaceAll('design/production-batches/monsters/batch07/M061/base-v2.png', sourceBase)
  .replaceAll('interact',name)
  .replace(/protectedRegions:"[^"]*"/,`protectedRegions:${JSON.stringify(fixed)}`)
  .replace("repairScope:'PR #114 independent first attempt; no failure recovery'", "repairScope:'LUMA-ASSET-16 independent first attempt; inherited 3/3 remains locked; no recovery authorized'")
  .replace('// Independent M061 HIT candidate.',`// Independent ${id} ${action} candidate.`)
  .replace(/  if\(frame===3\).*\n/,'');
 fs.writeFileSync(output+'/rig.cjs',code);
 fs.writeFileSync(output+'/candidate-clip.json',JSON.stringify({sessionId:'LUMA-ASSET-16',conceptId:id,species:null,evolutionStage:null,status:'CANDIDATE_ONLY',runtimeEnabled:false,productionEligible:false,sourceBase,canvas:{width:256,height:256},anchor:{x:0.5,y:1},anchorApproval:'PROPOSED_UNAPPROVED; measured bounds registration only',sourceFacing:id==='M061'?'UNCONFIRMED':'RIGHT',clip:{name:action,frames:8,frameDuration:duration,loop},movableRect:spec.rect,parts,anatomyScope:spec.anatomy,motion,artworkReview:'HUMAN_REVIEW_REQUIRED',naturalMotion:'HUMAN_REVIEW_REQUIRED',gui:'DEFERRED_GUI',wholeImageTransform:false,repairIterations:3,repairLimit:3,repairScope:'Inherited limit preserved; independent candidate first attempt, no failed asset repair'},null,2)+'\n');
 execFileSync(process.execPath,[output+'/rig.cjs'],{stdio:'inherit'});
}
