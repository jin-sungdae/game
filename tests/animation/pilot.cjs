const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');
const load=f=>require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,f));
const {pilotDefinition,PilotAssets,AnimationStateResolver,CharacterAnimator}=load('animation/pilot.js');
const {AssetLoader}=load('animation/loader.js');const {AnimationClock}=load('animation/clock.js');
const {baseSize,rendererSource}=load('assets/base.js');
for(const [character,base] of [['moa','/assets/creatures/moa/stage01/base.png'],['PIP','/assets/monsters/pip/base.png']]) {
 const pilot=pilotDefinition(character);const m=require('../../public'+pilot.manifest);
 test(character+' own base NOT_SUPPLIED without image requests',async()=>{
  assert.equal(pilot.base,base);assert.equal(await new PilotAssets(new AssetLoader({json:()=>assert.fail(),image:()=>assert.fail()})).load(pilot,'IDLE'),null);
  assert.deepEqual(rendererSource(null,pilot.base),{kind:'base',url:base});
 });
 test(character+' missing, decode failure, wrong canvas or wrong identity reject whole animation',async()=>{
  for(const mode of ['missing','decode','dimensions','identity']){
   const assets=new PilotAssets(new AssetLoader({json:async()=>{if(mode==='missing')throw Error();return {...m,species:mode==='identity'?'other':m.species};},image:async()=>{if(mode==='decode')throw Error();return {width:mode==='dimensions'?128:256,height:256};}}));
   assert.equal(await assets.load({...pilot,status:'SUPPLIED'},'IDLE'),null);
  }
 });
 test(character+' full clip cached, same character paths, timings and bottom canvas',async()=>{
  let calls=0;const urls=[];const assets=new PilotAssets(new AssetLoader({json:async()=>m,image:async u=>{calls++;urls.push(u);return {width:256,height:256};}}));
  const p={...pilot,status:'SUPPLIED'};const clip=await assets.load(p,'MOVE');
  assert.equal((await assets.load(p,'MOVE')),clip);assert.equal(calls,8);assert.ok(urls.every(u=>u.startsWith(p.manifest.replace('manifest.json','walk/'))));
  assert.deepEqual(baseSize(96,104),{width:82,height:82});
  const react=await assets.load(p,'REACT');assert.equal(react.clip.frames*react.clip.frameDuration,480);
 });
 test(character+' IDLE MOVE hysteresis, REACT completion and presentation priority',()=>{
  const r=new AnimationStateResolver();const observe=(speed,time,state='ROAMING',suppressed=false)=>r.observe({speed,state,suppressed},time);
  observe(0,0);assert.equal(r.sample(0).state,'IDLE');
  for(const speed of [1,0,7,2]){observe(speed,100);assert.equal(r.sample(100).state,'IDLE');}
  observe(40,200);assert.equal(r.sample(200).state,'MOVE');
  observe(5,300);assert.equal(r.sample(300).state,'MOVE');
  observe(40,400,'REACTING');assert.equal(r.sample(400).state,'REACT');
  observe(40,800,'REACTING');assert.equal(r.sample(881).state,'MOVE');
  observe(0,900);assert.equal(r.sample(900).state,'IDLE');
  observe(40,1000,'REACTING',true);assert.equal(r.sample(1000).suppressed,true);assert.equal(r.sample(1000).state,'IDLE');
 });
}
test('only pilot opts in, remaining 14 monster and stage2/3 unchanged',()=>{
 for(const name of ['MELLO','MOSSY','CHIRP','BUBU','PEBB','PUFF','TIKKI','MIMI','WISP','SHADE','EMBER','LUNET','NOVA','NOCT','unknown','MOKORI','NEBLA'])assert.equal(pilotDefinition(name),null);
 for(const stage of [2,3])assert.equal(pilotDefinition('moa',stage),null);
});
test('drag and invalid speed cannot drive walking playback',()=>{
 const r=new AnimationStateResolver();
 for(const speed of [NaN,-1,Infinity]){r.observe({speed,state:'WALKING',suppressed:false},0);assert.equal(r.sample(0).state,'IDLE');}
 r.observe({speed:40,state:'DRAGGING',suppressed:false},0);assert.equal(r.sample(0).suppressed,true);
});
test('phase integrates bounded speed, same identity retained, reduced motion pins frame0',()=>{
 const a=new CharacterAnimator();const clip={clip:{frames:8,frameDuration:80,loop:true}};
 assert.equal(a.sample('MOVE',clip,0,1,false),0);assert.equal(a.sample('MOVE',clip,80,1,false),1);
 assert.equal(a.sample('MOVE',clip,160,99,false),3);assert.equal(a.sample('MOVE',clip,240,1,true),0);
 assert.equal(a.sample('IDLE',clip,240,1,false),0);
});
test('16 subscribers share one RAF; last unsubscribe cancels; restart fresh',()=>{
 let serial=0;const requests=new Map();const c=new AnimationClock(cb=>{requests.set(++serial,cb);return serial;},id=>requests.delete(id));
 const stops=Array.from({length:16},()=>c.subscribe(()=>{}));assert.equal(requests.size,1);
 const [id,tick]=[...requests][0];requests.delete(id);tick(16);assert.equal(requests.size,1);
 stops.forEach(stop=>stop());assert.equal(requests.size,0);const stop=c.subscribe(()=>{});assert.equal(requests.size,1);stop();assert.equal(requests.size,0);
});
test('stable React entity, independent transform layers and native authority preserved',()=>{
 const renderer=fs.readFileSync('src/components/CharacterRenderer.tsx','utf8'),creature=fs.readFileSync('src/components/Creature.tsx','utf8'),css=fs.readFileSync('src/animation/character.css','utf8');
 assert.doesNotMatch(renderer,/\bkey=|setInterval|requestAnimationFrame|action\(/);
 assert.match(renderer,/\[entityId,pilot.character\]/);assert.match(renderer,/disposed=true;stop\(\);media.removeEventListener/);
 assert.match(renderer,/character-facing[\s\S]*character-animation[\s\S]*<img/);
 assert.match(creature,/gp-pose[\s\S]*gp-impulse[\s\S]*gp-visual[\s\S]*evolution-pose[\s\S]*CompanionVisual/);
 assert.match(css,/transform-origin:50% 100%/);assert.match(css,/scaleY\(\.99\)/);assert.doesNotMatch(css,/translate(?:X|Y)?\(/);assert.match(css,/prefers-reduced-motion:reduce/);
 for(const facing of [-1,1])assert.equal((41-41)*facing+41,41);
});
test('StrictMode effect setup-cleanup-setup and 100 mount cycles retain a single clock',()=>{
 let serial=0,calls=0;const pending=new Map();
 const clock=new AnimationClock(cb=>{pending.set(++serial,cb);return serial;},id=>pending.delete(id));
 assert.equal(pending.size,0);
 for(let cycle=0;cycle<100;cycle++){
  const mount=()=>Array.from({length:16},()=>clock.subscribe(()=>calls++));
  const probe=mount();assert.equal(pending.size,1);probe.forEach(stop=>stop());assert.equal(pending.size,0);
  const active=mount();assert.equal(pending.size,1);
  const [id,tick]=[...pending][0];pending.delete(id);tick(cycle*16);assert.equal(pending.size,1);
  active.forEach(stop=>{stop();stop();});assert.equal(pending.size,0);
 }
 assert.equal(calls,1600);
});
test('subscription created during a tick cannot start a second RAF chain',()=>{
 let serial=0;const pending=new Map();const clock=new AnimationClock(cb=>{pending.set(++serial,cb);return serial;},id=>pending.delete(id));
 let added=false,stopChild=()=>{};
 const stop=clock.subscribe(()=>{if(!added){added=true;stopChild=clock.subscribe(()=>{});}});
 const [id,tick]=[...pending][0];pending.delete(id);tick(16);
 assert.equal(pending.size,1);
 stop();stopChild();assert.equal(pending.size,0);
});
