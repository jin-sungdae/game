const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),Module=require('node:module');
const cue={commandId:'00000000-0000-0000-0000-000000000001',skillCode:'MOA_S1',species:'MOA',castMotion:'seed_inhale_leaf_release',element:'NATURE',assetStatus:'ASSET_REQUIRED',phases:['CAST_START','CHARGE','RELEASE','AREA','IMPACT','RECOVERY'].map(phase=>({phase,durationMs:100}))};
let receive;
const original=Module._load;
Module._load=function(request,...args){
 if(request==='@tauri-apps/api/event')return {listen:async(_,callback)=>{receive=callback;return ()=>{};}};
 if(request==='@tauri-apps/api/core')return {invoke:async()=>({game:{battle:null}})};
 return original.call(this,request,...args);
};
const {connect,skillTimeline}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'stores/entities.js'));
Module._load=original;
test('world listener observes cues without a mounted panel and keeps elapsed time across panel changes',async()=>{
 const previous=global.performance;let now=0;global.performance={now:()=>now};
 try {
 await connect();
 const world=(id,c,interaction)=>receive({payload:{game:{battle:{battleId:id,skillCue:c}},interaction}});
 world('battle-1',cue,'BATTLE_ITEMS');
 assert.equal(skillTimeline.sample(performance.now(),false,false).phase,'CAST_START');
 assert.equal(skillTimeline.sample(performance.now()+1000,false,false),null);
 now=1000;
 world('battle-1',cue,'ENCOUNTER');
 assert.equal(skillTimeline.sample(performance.now(),false,false),null);
 world('battle-2',null,'ENCOUNTER');
 assert.equal(skillTimeline.sample(performance.now(),false,false),null);
 } finally {global.performance=previous;}
});
