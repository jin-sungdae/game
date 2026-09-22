const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');const Module=require('node:module');
// Static React render only. Tauri invoke is stubbed; this is not native mouse/focus evidence.
const original=Module._load;Module._load=function(request,...args){if(request.endsWith('/overlay/bridge'))return {action:()=>{throw Error('render must not mutate');}};return original.call(this,request,...args);};
const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');
const {ItemInteraction}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'components/ItemInteraction.js'));Module._load=original;
const owned=[['SMALL_POTION','Small Potion'],['BOND_BERRY','Bond Berry'],['CAPTURE_CHARM','Capture Charm']].map(([itemCode,itemName])=>({itemCode,itemName,itemType:itemCode==='BOND_BERRY'?'COMPANION_CONSUMABLE':'BATTLE_CONSUMABLE',quantity:1}));
const view={busy:false,error:null,feedback:null,inventory:{gold:47,shop:owned.map(i=>({...i,price:123,ownedQuantity:7,maxStack:99})),owned,effects:[]}};
const render=(mode,changes={},battleActive=false,otherBusy=false)=>renderToStaticMarkup(React.createElement(ItemInteraction,{view:{...view,...changes},mode,battleActive,otherBusy}));
test('shop HTML displays server price/gold/owned and three explicit BUY buttons',()=>{const html=render('SHOP');assert.match(html,/Gold 47 G/);assert.match(html,/123 G/);assert.match(html,/Owned 7\/99/);assert.equal((html.match(/>BUY</g)||[]).length,3);assert.doesNotMatch(html,/autofocus/i);});
test('battle inventory excludes berry including a shop round trip context',()=>{const html=render('INVENTORY',{},true);assert.match(html,/Small Potion/);assert.match(html,/Capture Charm/);assert.doesNotMatch(html,/Bond Berry/);});
test('companion inventory only offers Berry',()=>{const html=render('INVENTORY');assert.match(html,/Bond Berry/);assert.doesNotMatch(html,/Small Potion|Capture Charm/);});
test('busy and unavailable ownership disable item use',()=>{assert.match(render('INVENTORY',{busy:true}),/disabled="">USE/);assert.match(render('INVENTORY',{},false,true),/disabled="">USE/);const inventory={...view.inventory,owned:[{...owned[1],quantity:0}]};assert.match(render('INVENTORY',{inventory}),/disabled="">USE/);});
test('server effect feedback and failure are rendered without derived magnitudes',()=>{assert.match(render('BATTLE_ITEMS',{feedback:'HP +7'}),/HP \+7/);assert.match(render('SHOP',{error:'INSUFFICIENT_GOLD'}),/role="alert"[^]*INSUFFICIENT_GOLD/);});
