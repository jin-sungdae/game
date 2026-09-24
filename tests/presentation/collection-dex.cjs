const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const Module=require('node:module');
const {collectionDexModel,dexFilters}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'presentation/collectionDex.js'));
const view={records:[],discoveredCodes:[],busy:false,error:null};
const record={monsterCode:'PIP',monsterName:'PIP',captureCount:7,firstCapturedAt:'2026-09-20T01:02:03Z',lastCapturedAt:'2026-09-22T02:00:00Z'};
const original=Module._load;
let assetFailure=false;
Module._load=function(request,...args){
 if(request.endsWith('/overlay/bridge')) return {action:()=>{throw Error('render must not mutate');}};
 if(request.endsWith('/assets/useBaseAsset')) return {useBaseAsset:url=>({url:assetFailure?null:url,fail:()=>{}})};
 return original.call(this,request,...args);
};
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {CollectionDex}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'components/CollectionDex.js'));
Module._load=original;
const render=(changes={},otherBusy=false)=>renderToStaticMarkup(React.createElement(CollectionDex,{view:{...view,...changes},otherBusy}));
test('30 slots include disabled provisional and Alpha candidates with stable Dex numbers',()=>{
 const m=collectionDexModel(view); assert.equal(m.total,30); assert.equal(m.slots.length,30);
 assert.deepEqual(m.slots.map(s=>s.dexNo),Array.from({length:30},(_,i)=>i+1));
 assert.equal(m.captured,0); assert.equal(m.discovered,0);
 assert.equal((render().match(/class="dex-slot"/g)||[]).length,30);
});
test('undiscovered model and markup never expose actual name or asset path',()=>{
 const model=collectionDexModel(view);
 assert.ok(model.slots.every(s=>s.name==='???'&&s.asset===null&&s.captureCount===null));
 assert.doesNotMatch(JSON.stringify(model),/PIP|pip\/base|MONSTER_002|Spring blob/);
 const html=render(); assert.doesNotMatch(html,/PIP|\/assets\/|MONSTER_|Spring blob|<img/);
 assert.match(html,/No\. 030/); assert.match(html,/UNDISCOVERED/);
});
test('discovery uses supplied server evidence, not catalog membership',()=>{
 const m=collectionDexModel({...view,discoveredCodes:['PIP','PIP','UNKNOWN']});
 assert.equal(m.discovered,1); assert.equal(m.captured,0); assert.equal(m.slots[0].state,'DISCOVERED');
 assert.equal(m.slots[0].name,'PIP'); assert.equal(m.slots[0].asset,null);
 const html=render({discoveredCodes:['PIP']}); assert.match(html,/아직 포획하지 않음/); assert.match(html,/COMMON/); assert.doesNotMatch(html,/\/assets\//);
});
test('capture count/date come verbatim from Collection and capture implies discovery',()=>{
 const m=collectionDexModel({...view,records:[record]}); assert.equal(m.captured,1); assert.equal(m.discovered,1);
 assert.equal(m.slots[0].captureCount,7); assert.equal(m.slots[0].firstCapturedAt,record.firstCapturedAt);
 const html=render({records:[record]}); assert.match(html,/Captured ×7/); assert.match(html,/dateTime="2026-09-20T01:02:03Z"/i);
 assert.match(html,/src="\/assets\/monsters\/pip\/base.png"/);
});
test('all rarity filters preserve full counts and exact distribution',()=>{
 assert.deepEqual(dexFilters,['ALL','COMMON','UNCOMMON','RARE','EPIC','SPECIAL']);
 assert.deepEqual(dexFilters.map(f=>collectionDexModel(view,f).slots.length),[30,8,7,6,5,4]);
 const filtered=collectionDexModel({...view,records:[record]},'SPECIAL');
 assert.equal(filtered.total,30); assert.equal(filtered.captured,1); assert.equal(filtered.discovered,1);
 assert.match(render(),/aria-label="Rarity filter"/);
});
test('asset failure and unproduced captured slots remain diagnostic with server counts',()=>{
 assetFailure=true; const html=render({records:[record]}); assetFailure=false;
 assert.doesNotMatch(html,/<img/); assert.match(html,/dex-silhouette/); assert.match(html,/Captured ×7/);
 const m=collectionDexModel({...view,records:[{...record,monsterCode:'MONSTER_005'}]});
 assert.equal(m.slots[4].asset,null); assert.equal(m.slots[4].name,'???'); assert.equal(m.slots[4].captureCount,7);
});
test('empty, unloaded, loading and failed refresh remain distinct',()=>{
 assert.match(render(),/아직 포획한 Monster가 없습니다/);
 const initial=collectionDexModel(); assert.equal(initial.captured,null); assert.equal(initial.discovered,null);
 assert.match(render({records:null,busy:true}),/Collection 불러오는 중/);
 assert.match(render({records:null,busy:true}),/disabled="">Refresh/);
 const failed=render({records:null,error:'offline'}); assert.match(failed,/role="alert"/); assert.match(failed,/불러오지 못했습니다/); assert.doesNotMatch(failed,/Captured 0/);
 const stale=render({records:[record],error:'offline'}); assert.match(stale,/마지막 확인 기록/); assert.match(stale,/Captured ×7/);
 assert.match(render({},true),/disabled="">Refresh/);
});
test('scroll/layout and reduced-motion contract fits existing compact panel',()=>{
 const css=fs.readFileSync('src/presentation/collectionDex.css','utf8');
 assert.match(css,/\.dex-list\{[^}]*flex:1;min-height:0;overflow-y:auto;overflow-x:hidden/);
 assert.match(css,/grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)[^]*animation:none!important;transition:none!important/);
 assert.match(css,/object-position:bottom center/);
 const geometry=fs.readFileSync('src-tauri/src/geometry.rs','utf8');
 assert.match(geometry,/MENU_SIZE: Size = Size \{\s*width: 240.0,\s*height: 300.0/);
});
test('Dex reuses nonactivating panel with explicit actions and no focus APIs',()=>{
 const html=render(); assert.doesNotMatch(html,/autofocus|<input|<select/i);
 const component=fs.readFileSync('src/components/CollectionDex.tsx','utf8');
 assert.doesNotMatch(component,/\.focus\(|setFocus|window\.open|setInterval|requestAnimationFrame/);
 assert.match(component,/action\('dex-refresh'\)/); assert.match(component,/action\('close'\)/);
 const native=fs.readFileSync('src-tauri/native/panel.m','utf8');
 assert.match(native,/canBecomeKeyWindow \{ return NO;/); assert.match(native,/canBecomeMainWindow \{ return NO;/);
 const main=fs.readFileSync('src-tauri/src/main.rs','utf8');
 assert.match(main,/\.focused\(false\)[^]*\.focusable\(false\)/);
 assert.match(main,/"dex" \| "dex-refresh"/);
 assert.match(main,/world\.view\.dex\.loaded_dex\(&value\)/);
 assert.match(main,/world\.view\.dex\.captured\(&c\)/);
});

test('all five activated species project their own Dex identity, rarity, asset and server count',()=>{
 const codes=['PIP','MELLO','MOSSY','CHIRP','BUBU'];const numbers=[1,2,3,4,6];
 const records=codes.map((monsterCode,i)=>({...record,monsterCode,monsterName:monsterCode,captureCount:i+1}));
 const m=collectionDexModel({...view,records});assert.equal(m.captured,5);assert.equal(m.discovered,5);
 for(const [i,code] of codes.entries()){
  const slot=m.slots.find(s=>s.dexNo===numbers[i]);assert.equal(slot.name,code);assert.equal(slot.rarity,'COMMON');
  assert.equal(slot.asset,`/assets/monsters/${code.toLowerCase()}/base.png`);assert.equal(slot.captureCount,i+1);
 }
});

test(process.env.LUMA_TEST_COLLECTION_OUTPUT ? 'Batch2 live HTTP Collection projects into the real Dex' : 'Batch2 captures preserve independent Dex assets, rarity and timestamps',()=>{
 const codes=['PEBB','PUFF','TIKKI','MIMI','WISP'];
 const records=process.env.LUMA_TEST_COLLECTION_OUTPUT
  ? JSON.parse(fs.readFileSync(process.env.LUMA_TEST_COLLECTION_OUTPUT,'utf8'))
  : codes.map(monsterCode=>({...record,monsterCode,monsterName:monsterCode,captureCount:1}));
 const model=collectionDexModel({...view,records});
 assert.equal(model.captured,5);
 for(const code of codes){
  const slot=model.slots.find(s=>s.name===code);
  const row=records.find(r=>r.monsterCode===code);
  assert.equal(slot.state,'CAPTURED');assert.equal(slot.captureCount,1);
  assert.equal(slot.firstCapturedAt,row.firstCapturedAt);
  assert.equal(slot.rarity,['PEBB','PUFF'].includes(code)?'COMMON':'UNCOMMON');
  assert.equal(slot.asset,`/assets/monsters/${code.toLowerCase()}/base.png`);
 }
});

test(process.env.LUMA_TEST_BATCH3_COLLECTION_OUTPUT ? 'Batch3 actual HTTP captures project to Dex with independent assets and rarity' : 'final Batch3 discovery and capture projection retains identity and timestamps',()=>{
 const codes=['SHADE','EMBER','LUNET','NOVA','NOCT'];const numbers=[15,16,19,21,28];
 const records=process.env.LUMA_TEST_BATCH3_COLLECTION_OUTPUT
  ? JSON.parse(fs.readFileSync(process.env.LUMA_TEST_BATCH3_COLLECTION_OUTPUT,'utf8'))
  : codes.map(monsterCode=>({...record,monsterCode,monsterName:monsterCode,captureCount:1}));
 const discovered=collectionDexModel({...view,discoveredCodes:codes});
 const captured=collectionDexModel({...view,records});
 assert.equal(discovered.discovered,5);assert.equal(captured.captured,5);
 for(const [i,code] of codes.entries()){
  assert.equal(discovered.slots.find(s=>s.dexNo===numbers[i]).state,'DISCOVERED');
  const slot=captured.slots.find(s=>s.dexNo===numbers[i]);const row=records.find(r=>r.monsterCode===code);
  assert.equal(slot.state,'CAPTURED');assert.equal(slot.name,code);assert.equal(slot.captureCount,1);
  assert.equal(slot.firstCapturedAt,row.firstCapturedAt);
  assert.equal(slot.rarity,code==='SHADE'?'UNCOMMON':code==='NOCT'?'SPECIAL':'RARE');
  assert.equal(slot.asset,`/assets/monsters/${code.toLowerCase()}/base.png`);
 }
});

test('Dex copy reflects restart-persistent server discovery',()=>{
 const html=render({discoveredCodes:['PIP']});
 assert.match(html,/발견·포획 기록은 서버에 저장됩니다/);
 assert.doesNotMatch(html,/현재 실행 기준/);
});
