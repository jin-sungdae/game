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
 const m=collectionDexModel({...view,records:[{...record,monsterCode:'MONSTER_002'}]});
 assert.equal(m.slots[1].asset,null); assert.equal(m.slots[1].name,'???'); assert.equal(m.slots[1].captureCount,7);
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
 assert.match(main,/world\.view\.dex\.loaded\(value\.clone\(\)\)/);
 assert.match(main,/world\.view\.dex\.captured\(&c\)/);
});
