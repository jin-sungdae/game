const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const {AssetLoader,browserIO}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/loader.js'));
const {PilotAssets,pilotDefinition}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'animation/pilot.js'));
const {rendererSource}=require(path.join(process.env.LUMA_ANIMATION_TEST_DIR,'assets/base.js'));
test('static MOA IDLE lookup never uses fetch, keeps unavailable states and own-base fallback',async()=>{
 const old=global.fetch;global.fetch=()=>assert.fail('manifest fetch forbidden');
 try{
  let images=0;const assets=new PilotAssets(new AssetLoader({json:browserIO.json,image:async()=>{images++;return {width:256,height:256};}}));const moa=pilotDefinition('moa');
  const clip=await assets.load(moa,'IDLE');assert.equal(clip.urls.length,4);assert.equal(clip.clip.frameDuration,450);
  for(const state of ['MOVE','REACT','INVALID','toString'])assert.equal(await assets.load(moa,state),null);
  for(const state of ['IDLE','MOVE','REACT'])assert.equal(await assets.load(pilotDefinition('PIP'),state),null);
  assert.equal(images,4);
  for(const mode of ['missing','invalid','missing-frame']){
   const io={json:mode==='invalid'?async()=>({species:'wrong'}):browserIO.json,image:async()=>{throw Error('missing frame');}};
   const p=mode==='missing'?{...moa,manifest:'/assets/creatures/unknown/stage01/manifest.json'}:moa;
   const missing=await new PilotAssets(new AssetLoader(io)).load(p,'IDLE');assert.equal(missing,null);
   assert.deepEqual(rendererSource(missing,moa.base),{kind:'base',url:'/assets/creatures/moa/stage01/base.png'});
  }
  for(const url of ['https://example.invalid/manifest.json','__proto__','/assets/creatures/moa/stage01/Manifest.json'])await assert.rejects(browserIO.json(url));
  const a=await browserIO.json(moa.manifest);a.animations.idle.frames=999;assert.equal((await browserIO.json(moa.manifest)).animations.idle.frames,6);
 }finally{global.fetch=old;}
});
test('document-start request observer counts rejected manifest attempts and resources',async()=>{
 const listeners={};let label='',observer;let calls=0;
 const context={performance:{now:()=>42},fetch:()=>{calls++;return Promise.reject(Error('CSP'));},XMLHttpRequest:function(){},addEventListener:(name,fn)=>listeners[name]=fn,PerformanceObserver:class{constructor(fn){observer=fn;}observe(){}},document:{createElement:()=>({style:{},setAttribute:(k,v)=>{if(k==='aria-label')label=v;}}),body:{append(){}}}};
 context.XMLHttpRequest.prototype.open=function(){};vm.createContext(context);vm.runInContext(fs.readFileSync('scripts/gui_qa/metadata_audit.js','utf8'),context);listeners.DOMContentLoaded();
 await assert.rejects(context.fetch('/assets/creatures/moa/stage01/manifest.json'));new context.XMLHttpRequest().open('GET','/other/manifest.json');
 observer({getEntries:()=>[{name:'tauri://localhost/assets/frame.png',initiatorType:'img',startTime:1,duration:2}]});listeners.securitypolicyviolation({effectiveDirective:'connect-src',blockedURI:'tauri://localhost/assets/manifest.json'});
 const trace=JSON.parse(label.replace('LUMA_METADATA_AUDIT ',''));assert.equal(calls,1);assert.equal(trace.fetchAttempts,1);assert.equal(trace.xhrAttempts,1);assert.equal(trace.manifestAttempts,2);assert.equal(trace.cspViolations,1);assert.equal(trace.resources.length,1);
});
