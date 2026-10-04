const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveFloating,settleApplicability}=load('animation/floating.js');const {PilotAssets,pilotDefinition,CharacterAnimator}=load('animation/pilot.js');const {AssetLoader}=load('animation/loader.js');
const p=pilotDefinition('PUFF'),m=require('../../public'+p.manifest);
function input(speed,active=true){return {state:'ROAMING',suppressed:false,floating:{timestamp:1,x:10,y:10,vx:0,vy:speed,speed,active,facing:-1}};}
test('FLOAT follows native excursion through slow apex and ends directly, fixed visual rate',()=>{
 assert.equal(resolveFloating(input(0,false),'FLOAT').state,'HOVER');assert.equal(resolveFloating(input(2),'HOVER').state,'HOVER');
 assert.equal(resolveFloating(input(10),'HOVER').state,'FLOAT');assert.equal(resolveFloating(input(0),'FLOAT').state,'FLOAT');
 assert.equal(resolveFloating(input(20,false),'FLOAT').state,'HOVER');assert.equal(settleApplicability,'NOT_APPLICABLE');
 for(const speed of [0,5,20,100])assert.equal(resolveFloating(input(speed),'FLOAT').rate,1);
 const i=input(10);Object.freeze(i.floating);resolveFloating(i,'HOVER');assert.equal(i.floating.y,10);
});
test('higher priority and invalid telemetry suspend; no invented settling phase',()=>{
 for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING'])assert.equal(resolveFloating({...input(10),state},'FLOAT').suppressed,true);
 for(const i of [{},input(NaN),input(Infinity),input(257),{...input(10),suppressed:true},{...input(10),floating:null}])assert.equal(resolveFloating(i,'FLOAT').suppressed,true);
});
test('PUFF own static clips and reduced motion; unsupported states remain unavailable',async()=>{
 assert.equal(p.status,'SUPPLIED');assert.equal(p.base,'/assets/monsters/puff/base.png');
 const a=new PilotAssets(new AssetLoader({json:async()=>m,image:async()=>({width:256,height:256})}));
 for(const [state,count,cycle] of [['HOVER',4,2000],['FLOAT',6,1200],['SETTLE',2,400]]){
  const c=await a.load(p,state);assert.equal(c.clip.frames,count);assert.equal(c.clip.frameDuration*count,cycle);assert.ok(c.urls[0].endsWith('_01.png'));assert.ok(c.urls.every(u=>u.startsWith('/assets/monsters/puff/')));
  const animator=new CharacterAnimator();for(let i=0;i<count;i++)assert.equal(animator.sample(state,c,i*100,1,true),0);
 }
 for(const state of ['IDLE','MOVE','REACT','BLINK','JUMP','FLY','GLIDE'])assert.equal(await a.load(p,state),null);
});
test('missing/invalid manifest or frame returns null for own-base fallback',async()=>{
 for(const mode of ['missing','image','identity','canvas','timing'])for(const state of ['HOVER','FLOAT','SETTLE']){
  const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')throw Error();return {...m,species:mode==='identity'?'chirp':'puff',animations:mode==='timing'?Object.fromEntries(Object.entries(m.animations).map(([n,c])=>[n,{...c,frameDuration:1}])):m.animations}},image:async()=>{if(mode==='image')throw Error();return {width:mode==='canvas'?128:256,height:256}}}));assert.equal(await a.load(p,state),null);
 }
});
