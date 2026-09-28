const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation',f));
const {PilotAssets,pilotDefinition,AnimationStateResolver,CharacterAnimator}=load('pilot.js');const {AssetLoader,browserIO}=load('loader.js');const {IdleSequencer}=load('idle.js');const {rendererSource}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'assets/base.js'));
const make=(image=async()=>({width:256,height:256}))=>new PilotAssets(new AssetLoader({json:browserIO.json,image}));
test('PIP pilot static lookup: own IDLE4 MOVE8 REACT6, no Blink or MOA fallback',async()=>{
 const p=pilotDefinition('PIP');assert.equal(p.status,'PRODUCTION_PILOT');assert.equal(p.base,'/assets/monsters/pip/base.png');const old=global.fetch;global.fetch=()=>assert.fail('no manifest fetch');
 try{const a=make();for(const [state,n,ms,loop] of [['IDLE',4,450,true],['MOVE',8,80,true],['REACT',6,80,false]]){const c=await a.load(p,state);assert.equal(c.urls.length,n);assert.equal(c.clip.frameDuration,ms);assert.equal(c.clip.loop,loop);assert.ok(c.urls.every(u=>u.startsWith('/assets/monsters/pip/')));}
 assert.equal(await a.load(p,'BLINK'),null);assert.equal(await a.load(p,'INVALID'),null);
 const idle=new IdleSequencer(()=>assert.fail('PIP has no blink schedule'));assert.equal(idle.sample(10000,true,false,undefined,270),'IDLE');
 }finally{global.fetch=old;}
});
test('missing/invalid PIP clip falls back atomically to PIP base and leaves other clips available',async()=>{
 const p=pilotDefinition('PIP');for(const [state,part] of [['IDLE','idle'],['MOVE','walk'],['REACT','react']])for(const invalid of [false,true]){
 const a=make(async u=>{if(u.includes('/'+part+'/')){if(!invalid)throw Error('missing');return {width:128,height:256};}return {width:256,height:256};});assert.equal(await a.load(p,state),null);assert.deepEqual(rendererSource(null,p.base),{kind:'base',url:'/assets/monsters/pip/base.png'});
 for(const other of ['IDLE','MOVE','REACT'].filter(x=>x!==state))assert.ok(await a.load(p,other));}
});
test('PIP measured GROUND motion selects MOVE under ROAMING, stop returns IDLE; higher presentation wins',()=>{
 const row=JSON.parse(fs.readFileSync('src/entities/monster-dex.json')).find(x=>x.monsterCode==='PIP');assert.equal(row.movementProfile,'GROUND');assert.equal(row.behaviorProfile,'PLAYFUL');
 const r=new AnimationStateResolver();r.observe({state:'ROAMING',speed:0,suppressed:false},0);assert.equal(r.sample(0).state,'IDLE');
 for(const speed of [14,16,24]){r.observe({state:'ROAMING',speed,suppressed:false},50);assert.equal(r.sample(50).state,'MOVE');}
 r.observe({state:'ROAMING',speed:0,suppressed:false},100);assert.equal(r.sample(100).state,'IDLE');
 for(const state of ['SPAWNING','DESPAWNING','BATTLE','ENGAGED']){r.observe({state,speed:24,suppressed:state!=='ENGAGED'},200);assert.equal(r.sample(200).suppressed,true);assert.notEqual(r.sample(200).state,'REACT');}
 // Existing encounter ENGAGED is suppressed, so actual mouse REACT is not applicable.
 const source=fs.readFileSync('src/components/Creature.tsx','utf8');for(const pattern of [/Boolean\(arrival\)/,/entity.state==='DESPAWNING'/,/Boolean\(game\?\.battle\)/,/effect!=='none'/,/entityId=\{monster\?\.encounterId/])assert.match(source,pattern);
});
test('PIP sequences on the existing animator and deterministic REACT completion',async()=>{
 const p=pilotDefinition('PIP'),assets=make();for(const [state,count,ms,loop] of [['IDLE',4,450,true],['MOVE',8,80,true],['REACT',6,80,false]]){
 const c=await assets.load(p,state),a=new CharacterAnimator(),order=[];let previous=-1;
 for(let t=0;t<=count*ms;t+=10){const f=a.sample(state,c,t,1,false);if(f!==previous){order.push(f);previous=f;}}
 assert.deepEqual(order,Array.from({length:count},(_,i)=>i).concat(loop?[0]:[]));assert.equal(a.sample(state,c,5000,1,true),0);}
 const r=new AnimationStateResolver();r.observe({state:'REACTING',speed:0,suppressed:false},0);assert.equal(r.sample(479).state,'REACT');assert.equal(r.sample(480).state,'IDLE');
});
