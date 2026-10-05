const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveFloating}=load('animation/floating.js');
const {PilotAssets,pilotDefinition,CharacterAnimator,floatingConsumers}=load('animation/pilot.js');
const {AssetLoader,browserIO}=load('animation/loader.js');
const input=(speed,active=true)=>({state:'ROAMING',suppressed:false,floating:{timestamp:1,x:0,y:0,vx:speed,vy:0,speed:Math.abs(speed),active,facing:speed<0?-1:1}});
const image=async url=>{const b=fs.readFileSync(path.join(__dirname,'../../public',url));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
test('explicit consumers share FLOATING dispatch, not per-character resolvers',()=>{
 assert.deepEqual(floatingConsumers,['PUFF','WISP','LUNET']);
 for(const code of floatingConsumers)assert.equal(pilotDefinition(code).floatingProfile,'FLOATING');
});
for(const code of floatingConsumers){
 const p=pilotDefinition(code);
 test(code+' static identity, sequence, cadence and reduced motion',async()=>{
  const a=new PilotAssets(new AssetLoader({...browserIO,image}));
  assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);
  for(const [state,count,duration] of [['HOVER',4,500],['FLOAT',6,200]]){
   const c=await a.load(p,state);assert.ok(c);assert.equal(c.clip.frameDuration,duration);
   assert.deepEqual(c.urls,Array.from({length:count},(_,i)=>`/assets/monsters/${code.toLowerCase()}/${state.toLowerCase()}/${state.toLowerCase()}_${String(i+1).padStart(2,'0')}.png`));
   const animator=new CharacterAnimator();
   for(let t=0;t<=count*duration*2;t+=20)assert.equal(animator.sample(state,c,t,1,false),Math.floor(t/duration)%count);
   assert.equal(animator.sample(state,c,count*duration*2+20,1,true),0);
  }
  if(code!=='PUFF')assert.equal(await a.load(p,'SETTLE'),null);
 });
 test(code+' same resolver holds slow apex, completes/cancels, suppresses lifecycle',()=>{
  let state='HOVER';
  for(const [sample,expected] of [[input(0,false),'HOVER'],[input(12),'FLOAT'],[input(0),'FLOAT'],[input(0,false),'HOVER'],[input(-12),'FLOAT'],[input(12,false),'HOVER']]){
   const snapshot=structuredClone(sample);const r=resolveFloating(sample,state);state=r.state;
   assert.equal(state,expected);assert.equal(r.rate,1);assert.deepEqual(sample,snapshot);
  }
  for(const s of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING'])assert.equal(resolveFloating({...input(12),state:s},'FLOAT').suppressed,true);
  assert.equal(resolveFloating({...input(12),suppressed:true},'FLOAT').suppressed,true);
  assert.equal(resolveFloating(input(12),'HOVER').state,'FLOAT');
 });
 test(code+' invalid/missing clip leaves only own-base fallback',async()=>{
  const m=await browserIO.json(p.manifest);
  for(const mode of ['missing','frame','identity','timing']){
   const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')throw Error();const v=structuredClone(m);if(mode==='identity')v.species='moa';if(mode==='timing')v.animations.float.frameDuration=100;return v},image:async u=>{if(mode==='frame')throw Error();return image(u)}}));
   assert.equal(await a.load(p,'FLOAT'),null);assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);
  }
 });
}
