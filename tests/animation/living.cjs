const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {livingSequence}=load('animation/living.js');
const {pilotDefinition,PilotAssets,AnimationStateResolver,CharacterAnimator}=load('animation/pilot.js');
const {AssetLoader}=load('animation/loader.js');
const {jumpFrame}=load('animation/jump.js');
const input=(kind='OBSERVE')=>({speed:0,state:'ROAMING',suppressed:false,livingCue:{kind,serial:1}});
for(const [code,kind,sequence] of [['PIP','REACT','REACT'],['MIMI','OBSERVE','PEEK'],['PUFF','REST','SETTLE'],['EMBER','REACT','INTENSE']]) {
 test(code+' native cue uses only its own existing animation',async()=>{
  const p=pilotDefinition(code), urls=[];const manifest=JSON.parse(fs.readFileSync('public'+p.manifest));
  const assets=new PilotAssets(new AssetLoader({json:async()=>manifest,image:async u=>{urls.push(u);return {width:256,height:256};}}));
  assert.equal(livingSequence(p,input(kind),false),sequence);
  assert.ok(await assets.load(p,sequence));assert.ok(urls.every(u=>u.startsWith('/assets/monsters/'+code.toLowerCase()+'/')));
 });
}
test('missing cues and unsupported species never borrow animations',()=>{
 for(const code of ['MOSSY','PEBB','TIKKI','WISP','LUNET','NOCT','SHADE','NOVA','CHIRP','BUBU','MELLO','moa']) assert.equal(livingSequence(pilotDefinition(code),input('REACT'),false),null);
});
test('movement, jumps, battle, lifecycle and reduced motion outrank attention',()=>{
 const p=pilotDefinition('MIMI');
 for(const patch of [{speed:3},{speed:NaN},{state:'ENGAGED'},{state:'SPAWNING'},{state:'DESPAWNING'},{suppressed:true},{jump:{progress:.5}},{livingCue:{kind:'OBSERVE',serial:NaN}}]) assert.equal(livingSequence(p,{...input(),...patch},false),null);
 assert.equal(livingSequence(p,input(),true),null);
 const resolver=new AnimationStateResolver();resolver.observe({speed:0,state:'ROAMING',suppressed:false},0);assert.equal(resolver.sample(0).state,'IDLE');
});
test('cue replay keeps phase, new cue restarts, reduced motion pins frame',()=>{
 const a=new CharacterAnimator(),clip={clip:{frames:5,frameDuration:120,loop:false}};
 assert.equal(a.sample('PEEK:1',clip,0,1,false),0);
 a.sample('PEEK:1',clip,100,1,false);assert.equal(a.sample('PEEK:1',clip,200,1,false),1);
 assert.equal(a.sample('PEEK:2',clip,210,1,false),0);
 assert.equal(a.sample('PEEK:2',clip,310,1,true),0);
});
test('renderer uses shared clock, suspends hidden subscription and preserves anchor/facing',()=>{
 const source=fs.readFileSync('src/components/CharacterRenderer.tsx','utf8');
 assert.match(source,/visibilitychange/);assert.match(source,/!document.hidden/);
 assert.match(source,/livingSequence\(pilot/);assert.match(source,/directionScale\(facing\)/);
 assert.doesNotMatch(source,/setInterval|requestAnimationFrame|setTimeout/);
});
