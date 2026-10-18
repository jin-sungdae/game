const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {AssetLoader}=load('animation/loader.js');
const {CharacterAnimator,AnimationStateResolver}=load('animation/pilot.js');
const {directionScale}=load('animation/model.js');
const manifest={species:'caplet',stage:1,canvas:{width:256,height:256},anchor:{x:.5,y:1},display:{width:82},animations:{sleep:{frames:6,frameDuration:400,loop:true}}};
test('candidate complete SLEEP clip uses existing loader and animator; missing frame fails closed',async()=>{
 const loader=new AssetLoader({json:async()=>manifest,image:async()=>({width:256,height:256})});
 const clip=await loader.loadRegistered('caplet',1,'/candidate/manifest.json','sleep');assert.ok(clip);
 const animator=new CharacterAnimator();const frames=new Set();
 for(let t=0;t<=2400;t+=10)frames.add(animator.sample('caplet:sleep',clip,t,1,false));
 assert.equal(frames.size,6);assert.equal(animator.sample('caplet:sleep',clip,2400,1,false),0);
 assert.equal(animator.sample('caplet:sleep',clip,2500,1,true),0);
 const bad=new AssetLoader({json:async()=>manifest,image:async url=>{if(url.endsWith('03.png'))throw Error('missing');return {width:256,height:256};}});
 assert.equal(await bad.loadRegistered('caplet',1,'/candidate/manifest.json','sleep'),null);
});
test('existing behavior resolver preserves sleep identity and suppression',()=>{
 const r=new AnimationStateResolver();const input={state:'SLEEPING',speed:0,suppressed:false};
 assert.equal(r.sampleCompanion(input,0).state,'SLEEP');
 assert.equal(r.sampleCompanion({...input,suppressed:true},0).suppressed,true);
 assert.deepEqual([directionScale(-1),directionScale(1)],[-1,1]);
});
