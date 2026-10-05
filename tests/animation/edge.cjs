const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {resolveEdge,turnApplicability}=load('animation/edge.js'),{PilotAssets,pilotDefinition,CharacterAnimator}=load('animation/pilot.js'),{AssetLoader,browserIO}=load('animation/loader.js'),{parseManifest}=load('animation/model.js');
const p=pilotDefinition('SHADE'),m=require('../../public'+p.manifest);
const input=speed=>Object.freeze({speed,state:'ROAMING',suppressed:false,x:20,y:60,facing:-1});
test('EDGE reads accepted speed with hysteresis, stop/resume and fixed smoke cadence',()=>{
 let state='IDLE';for(const [speed,expected] of [[0,'IDLE'],[7,'IDLE'],[8,'EDGE_MOVE'],[4,'EDGE_MOVE'],[3.001,'EDGE_MOVE'],[3,'IDLE'],[2,'IDLE'],[20,'EDGE_MOVE'],[0,'IDLE']]){const i=input(speed),s=resolveEdge(i,state);assert.equal(s.state,expected);assert.equal(s.rate,1);assert.equal(i.x,20);assert.equal(i.y,60);assert.equal(i.facing,-1);state=s.state;}
 assert.equal(p.status,'EDGE_PRODUCTION');
 assert.equal(turnApplicability,'NOT_APPLICABLE');
});
test('lifecycle and invalid motion suppress; no corner signal is invented',()=>{
 for(const state of ['SPAWNING','ENGAGED','BATTLE','CAPTURE','DESPAWNING','UNKNOWN'])assert.equal(resolveEdge({...input(20),state},'EDGE_MOVE').suppressed,true);
 for(const speed of [NaN,Infinity,-1,257])assert.equal(resolveEdge(input(speed),'EDGE_MOVE').suppressed,true);
 assert.equal(resolveEdge({...input(20),suppressed:true},'EDGE_MOVE').suppressed,true);
});
const assets=(json=browserIO.json,image=async url=>{const b=fs.readFileSync(path.join(process.cwd(),'public',url));return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})=>new PilotAssets(new AssetLoader({json,image}));
test('real registry/files order, cycles, reduced motion and deterministic TURN asset coverage',async()=>{
 for(const [state,count,duration,loop] of [['IDLE',5,440,true],['EDGE_MOVE',6,180,true],['TURN',3,120,false]]){
  const c=await assets().load(p,state);assert.equal(c.urls.length,count);assert.ok(c.urls[0].endsWith('_01.png'));assert.ok(c.urls[count-1].endsWith(`_0${count}.png`));assert.equal(c.clip.frameDuration,duration);
  const a=new CharacterAnimator();for(let t=0;t<=4400;t+=20)assert.equal(a.sample(state,c,t,1,false),loop?Math.floor(t/duration)%count:Math.min(count-1,Math.floor(t/duration)));
  assert.equal(a.sample('suppressed',null,4420,1,false),0);assert.equal(a.sample(state,c,4440,1,false),0);assert.equal(a.sample(state,c,4460,1,true),0);
 }
 for(const state of ['MOVE','REACT','PEEK','FLOAT','JUMP'])assert.equal(await assets().load(p,state),null);
});
test('missing/invalid asset resolves null for SHADE own-base; prefix cannot escape bundle',async()=>{
 assert.equal(p.base,'/assets/monsters/shade/base.png');
 for(const state of ['IDLE','EDGE_MOVE','TURN']){
  assert.equal(await assets(async()=>null).load(p,state),null);
  assert.equal(await assets(async()=>({...m,species:'pip'})).load(p,state),null);
  assert.equal(await assets(browserIO.json,async()=>{throw Error('missing')}).load(p,state),null);
 }
 for(const filePrefix of ['../edge','/edge','https://bad',null,1,''])assert.throws(()=>parseManifest({...m,animations:{edge_move:{...m.animations.edge_move,filePrefix}}},'shade',1));
});
