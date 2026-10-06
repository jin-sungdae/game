const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveEdge,turnApplicability}=load('animation/edge.js');
const {PilotAssets,pilotDefinition,CharacterAnimator,edgeConsumers}=load('animation/pilot.js');
const {AssetLoader,browserIO}=load('animation/loader.js');
const image=async url=>{const b=fs.readFileSync(path.join(process.cwd(),'public',url));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
test('SHADE and NOCT explicitly share EDGE dispatch',()=>{
 assert.deepEqual(edgeConsumers.map(c=>c.character),['SHADE','NOCT']);
 assert.equal(pilotDefinition('SHADE').status,'EDGE_PRODUCTION');assert.equal(pilotDefinition('NOCT').status,'SUPPLIED');
 assert.equal(turnApplicability,'NOT_APPLICABLE');
});
for(const code of edgeConsumers.map(c=>c.character)){
 const p=pilotDefinition(code);
 test(code+' same resolver hysteresis, lifecycle and world read-only contract',()=>{
  assert.equal(p.edgeProfile,'EDGE');let previous='IDLE';
  for(const [speed,expected] of [[0,'IDLE'],[7.99,'IDLE'],[8,'EDGE_MOVE'],[3.01,'EDGE_MOVE'],[3,'IDLE'],[7,'IDLE'],[20,'EDGE_MOVE'],[0,'IDLE']]){
   const input=Object.freeze({speed,state:'ROAMING',suppressed:false,x:5,y:7,facing:-1});const result=resolveEdge(input,previous);
   assert.equal(result.state,expected);assert.equal(result.rate,1);assert.deepEqual([input.x,input.y,input.facing],[5,7,-1]);previous=result.state;
  }
  for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING'])assert.equal(resolveEdge({speed:20,state,suppressed:false},'EDGE_MOVE').suppressed,true);
  assert.equal(resolveEdge({speed:20,state:'ROAMING',suppressed:true},'EDGE_MOVE').suppressed,true);
 });
 test(code+' real static registry/files, frame order, fixed cycles and reduced motion',async()=>{
  const assets=new PilotAssets(new AssetLoader({...browserIO,image}));
  for(const [state,name,prefix,count,duration] of [['IDLE','idle','idle',5,440],['EDGE_MOVE','edge_move','edge',6,180]]){
   const c=await assets.load(p,state);assert.ok(c);assert.equal(c.clip.frameDuration,duration);
   assert.deepEqual(c.urls,Array.from({length:count},(_,i)=>`/assets/monsters/${code.toLowerCase()}/${name}/${prefix}_${String(i+1).padStart(2,'0')}.png`));
   const animator=new CharacterAnimator();for(let t=0;t<=count*duration*2;t+=20)assert.equal(animator.sample(state,c,t,1,false),Math.floor(t/duration)%count);
   assert.equal(animator.sample(state,c,count*duration*2+20,1,true),0);
   assert.equal(animator.sample('suppressed',null,count*duration*2+40,1,false),0);
   assert.equal(animator.sample(state,c,count*duration*2+60,1,false),0);
  }
  if(code==='NOCT')assert.equal(await assets.load(p,'TURN'),null);
 });
 test(code+' missing and invalid assets retain own-base fallback',async()=>{
  assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);
  const m=await browserIO.json(p.manifest);
  for(const mode of ['missing','identity','frame','timing'])for(const state of ['IDLE','EDGE_MOVE']){
   const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')return null;const v=structuredClone(m);if(mode==='identity')v.species='pip';if(mode==='timing')v.animations[state==='IDLE'?'idle':'edge_move'].frameDuration=1;return v},image:async u=>{if(mode==='frame')throw Error();return image(u)}}));
   assert.equal(await a.load(p,state),null);
  }
 });
}
