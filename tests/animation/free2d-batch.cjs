const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {free2dConsumers,pilotDefinition,PilotAssets,CharacterAnimator}=load('animation/pilot.js');
const {resolveFree2d,intenseApplicability}=load('animation/free2d.js');
const {AssetLoader,browserIO}=load('animation/loader.js');
const image=async u=>{const b=fs.readFileSync(path.join(process.cwd(),'public',u));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}};
test('EMBER/NOVA share FREE_2D consumer contract; NOVA has no INTENSE delivery',async()=>{
 assert.deepEqual(free2dConsumers,['EMBER','NOVA']);assert.equal(intenseApplicability,'NOT_APPLICABLE');
 assert.equal(await new PilotAssets(new AssetLoader({...browserIO,image})).load(pilotDefinition('NOVA'),'INTENSE'),null);
});
for(const code of free2dConsumers){
 const p=pilotDefinition(code);
 test(code+' vectors, hysteresis and completion use same read-only resolver',()=>{
  assert.equal(p.free2dProfile,'FREE_2D');
  for(const [vx,vy] of [[10,0],[-10,0],[0,10],[0,-10],[6,8],[-6,-8]]){
   const input=Object.freeze({speed:Math.hypot(vx,vy),state:'ROAMING',suppressed:false,x:120,y:30,vx,vy,target:200,facing:-1});
   assert.deepEqual(resolveFree2d(input,'FLICKER'),{state:'FLOW',suppressed:false,rate:1});assert.equal(input.x,120);assert.equal(input.facing,-1);
  }
  let state='FLICKER';for(const [speed,next] of [[7.999,'FLICKER'],[8,'FLOW'],[3.001,'FLOW'],[3,'FLICKER'],[8,'FLOW'],[0,'FLICKER']]){const r=resolveFree2d({speed,state:'ROAMING',suppressed:false},state);assert.equal(r.state,next);assert.equal(r.rate,1);state=next;}
  for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING'])assert.equal(resolveFree2d({speed:20,state,suppressed:false},'FLOW').suppressed,true);
 });
 test(code+' real static registry, fixed cadence, reduced motion and own-base fallback',async()=>{
  assert.equal(p.base,`/assets/monsters/${code.toLowerCase()}/base.png`);
  for(const [state,count,duration] of [['FLICKER',5,360],['FLOW',6,160]]){
   const c=await new PilotAssets(new AssetLoader({...browserIO,image})).load(p,state);assert.ok(c);assert.equal(c.urls.length,count);assert.equal(c.clip.frameDuration,duration);
   const a=new CharacterAnimator();for(let t=0;t<4000;t+=40)assert.equal(a.sample(state,c,t,1,false),Math.floor(t/duration)%count);assert.equal(a.sample(state,c,4040,1,true),0);
   for(const mode of ['missing','identity','frame','timing']){
    const io={json:async()=>{if(mode==='missing')return null;const m=structuredClone(await browserIO.json(p.manifest));if(mode==='identity')m.species='pip';if(mode==='timing')m.animations[state.toLowerCase()].frameDuration=99;return m},image:async u=>{if(mode==='frame')throw Error('missing');return image(u)}};
    assert.equal(await new PilotAssets(new AssetLoader(io)).load(p,state),null);
   }
  }
 });
}
