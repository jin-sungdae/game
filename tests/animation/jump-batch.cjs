const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {jumpFrame}=load('animation/jump.js');const {jumpConsumers,pilotDefinition,PilotAssets}=load('animation/pilot.js');const {AssetLoader,browserIO}=load('animation/loader.js');
const image=async u=>{const b=fs.readFileSync(path.join(process.cwd(),'public',u));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
const sample=(phase,progress,vy,grounded=false)=>({phase,progress,vy,grounded,x:100,y:grounded?0:10,vx:20,timestamp:1,facing:1});
test('MELLO/BUBU share JUMP dispatch and existing same-render ground snapshot path',()=>{
 assert.deepEqual(jumpConsumers.map(c=>c.character),['MELLO','BUBU']);assert.equal(pilotDefinition('MELLO').status,'JUMP_PRODUCTION');assert.equal(pilotDefinition('BUBU').status,'SUPPLIED');
 const s=fs.readFileSync('src/components/CharacterRenderer.tsx','utf8');assert.match(s,/const nativeFrame=jumpFrame\(input.jump/);assert.match(s,/frame:nativeFrame\?\?0/);
});
for(const code of jumpConsumers.map(c=>c.character)){
 const p=pilotDefinition(code);
 test(code+' original eight-frame pack and slots, no timer-driven playback',async()=>{
  assert.equal(p.jumpProfile,'JUMP');assert.equal(p.sourceFacing,'RIGHT');
  const a=new PilotAssets(new AssetLoader({...browserIO,image}));const c=await a.load(p,'JUMP');assert.ok(c);assert.equal(c.clip.frames,8);assert.equal(c.clip.loop,false);
  assert.deepEqual(c.urls,Array.from({length:8},(_,i)=>`/assets/monsters/${code.toLowerCase()}/jump/jump_0${i+1}.png`));
  for(const [phase,progress,vy,grounded,index] of [['LAUNCH',0,40,false,2],['ASCEND',.2,20,false,3],['APEX',.45,4,false,4],['APEX',.55,-4,false,4],['DESCEND',.8,-20,false,5],['LAND',1,0,true,6]]){
   const s=Object.freeze(sample(phase,progress,vy,grounded));assert.equal(jumpFrame(s,false,false),index);assert.equal(jumpFrame({...s,timestamp:9999},false,false),index);assert.equal(jumpFrame(s,true,false),null);assert.equal(jumpFrame(s,false,true),null);
  }
  for(const phase of ['NEUTRAL','CROUCH','SETTLE'])assert.equal(jumpFrame(sample(phase,.1,1),false,false),null);
  for(const state of ['IDLE','MOVE','REACT','BLINK'])assert.equal(await a.load(p,state),null);
 });
 test(code+' ground contact rejects airborne LAND and stale grounded DESCEND immediately',()=>{
  assert.equal(jumpFrame(sample('DESCEND',.99,-20),false,false),5);
  assert.equal(jumpFrame(sample('LAND',1,0,true),false,false),6);
  assert.equal(jumpFrame(sample('LAND',.9,0,false),false,false),null);
  assert.equal(jumpFrame(sample('DESCEND',1,-20,true),false,false),null);
  for(const s of [null,sample('ASCEND',.2,-2),sample('DESCEND',.8,2),sample('APEX',NaN,0)])assert.equal(jumpFrame(s,false,false),null);
  for(const priority of ['SPAWNING','RARITY','ENGAGED','BATTLE','CAPTURE','DESPAWNING'])assert.equal(jumpFrame(sample('ASCEND',.2,2),true,false),null,priority);
 });
 test(code+' missing/invalid pack falls to own base only',async()=>{
  assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);const m=await browserIO.json(p.manifest);
  for(const mode of ['missing','identity','frame','count','phases','loop']){
   const a=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')return null;const v=structuredClone(m);if(mode==='identity')v.species='pip';if(mode==='count')v.animations.jump.frames=5;if(mode==='phases')v.jumpPhases=[];if(mode==='loop')v.animations.jump.loop=true;return v},image:async u=>{if(mode==='frame')throw Error();return image(u)}}));assert.equal(await a.load(p,'JUMP'),null);
  }
 });
}
