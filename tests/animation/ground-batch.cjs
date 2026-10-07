const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {groundConsumers,groundClips,pilotDefinition,PilotAssets,AnimationStateResolver,CharacterAnimator}=load('animation/pilot.js');
const {AssetLoader,browserIO}=load('animation/loader.js');
const image=async url=>{const b=fs.readFileSync(path.join(process.cwd(),'public',url));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
test('four consumers use existing resolver and profile-driven clip contract',()=>{
 assert.deepEqual(groundConsumers.map(c=>c.character),['PIP','MOSSY','PEBB','TIKKI']);
 assert.deepEqual(groundClips,{IDLE:{frames:4,frameDuration:450},MOVE:{frames:8,frameDuration:80}});
 const source=fs.readFileSync('src/animation/pilot.ts','utf8');assert.doesNotMatch(source,/p\.character\s*===\s*'PIP'/);
});
for(const code of groundConsumers.map(c=>c.character)){
 const p=pilotDefinition(code);
 test(code+' static registry, IDLE4/MOVE8 frame order and rate integration',async()=>{
  assert.equal(p.groundProfile,'GROUND');assert.equal(p.sourceFacing,'RIGHT');
  const assets=new PilotAssets(new AssetLoader({...browserIO,image}));
  for(const [state,count,duration] of [['IDLE',4,450],['MOVE',8,80]]){
   const c=await assets.load(p,state);assert.ok(c);assert.equal(c.clip.frames,count);assert.equal(c.clip.frameDuration,duration);
   const name=state==='IDLE'?'idle':p.groundMoveClip,first=code==='PIP'?0:1;
   assert.deepEqual(c.urls,Array.from({length:count},(_,i)=>`/assets/monsters/${code.toLowerCase()}/${name}/${name}_${String(i+first).padStart(2,'0')}.png`));
   for(const rate of state==='MOVE'?[.5,1,2]:[1]){
    const a=new CharacterAnimator();for(let t=0;t<=count*duration*2/rate;t+=10)assert.equal(a.sample(state,c,t,rate,false),Math.floor(t*rate/duration)%count);
    assert.equal(a.sample(state,c,10000,rate,true),0);
   }
  }
  if(code!=='PIP')assert.equal(await assets.load(p,'REACT'),null);
 });
 test(code+' stationary, sleepy speed, passive pause, curious approach and bounded rate',()=>{
  const r=new AnimationStateResolver();
  for(const [speed,state,rate] of [[0,'IDLE',1],[2,'IDLE',1],[8,'MOVE',.5],[0,'IDLE',1],[14,'MOVE',.5],[40,'MOVE',1],[100,'MOVE',2],[3,'MOVE',.5],[2.9,'IDLE',1]]){
   const input=Object.freeze({speed,state:'ROAMING',suppressed:false});r.observe(input,1000);const result=r.sample(1000);assert.equal(result.state,state);assert.equal(result.rate,rate);assert.equal(input.speed,speed);
  }
  // Caller-owned spawn/rarity/battle/capture/despawn priority remains authoritative.
  for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING']){r.observe({speed:40,state,suppressed:true},2000);assert.equal(r.sample(2000).suppressed,true);}
  r.observe({speed:0,state:'ROAMING',suppressed:false},3000);assert.equal(r.sample(3000).state,'IDLE');
 });
 test(code+' missing/invalid clips fail to own base, never another identity',async()=>{
  assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);const m=await browserIO.json(p.manifest);
  for(const mode of ['missing','identity','frame','count','timing','loop'])for(const state of ['IDLE','MOVE']){
   const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')return null;const v=structuredClone(m),clip=v.animations[state==='IDLE'?'idle':p.groundMoveClip];if(mode==='identity')v.species='moa';if(mode==='count')clip.frames=6;if(mode==='timing')clip.frameDuration=1;if(mode==='loop')clip.loop=false;return v},image:async u=>{if(mode==='frame')throw Error();return image(u)}}));assert.equal(await a.load(p,state),null);
  }
 });
}
test('profile rather than character name controls four-frame IDLE; unknown profile cannot bypass legacy contract',async()=>{
 const p=pilotDefinition('MOSSY');const a=new PilotAssets(new AssetLoader({...browserIO,image}));
 assert.equal((await a.load({...p,character:'MOA'},'IDLE')).clip.frames,4);
 assert.equal(await a.load({...p,groundProfile:undefined},'IDLE'),null);
});
