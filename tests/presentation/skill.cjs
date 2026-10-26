const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const {SkillTimeline,validSkillCue}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'skill.js'));
const cue={commandId:'00000000-0000-0000-0000-000000000001',skillCode:'MOA_S1',species:'MOA',castMotion:'seed_inhale_leaf_release',element:'NATURE',assetStatus:'ASSET_REQUIRED',phases:['CAST_START','CHARGE','RELEASE','AREA','IMPACT','RECOVERY'].map(phase=>({phase,durationMs:100}))};
test('server phases and separate motion/effect identity; no invented sprites',()=>{let t=new SkillTimeline();t.observe(cue,0);for(let i=0;i<6;i++){let p=t.sample(i*100,false,false);assert.equal(p.phase,cue.phases[i].phase);assert.equal(p.bodyMotion,cue.castMotion);assert.equal(p.effect,'NATURE');assert.equal(p.assetStatus,'ASSET_REQUIRED');}assert.equal(t.sample(600,false,false),null);});
test('duplicate, reduced motion, hidden and malformed timelines',()=>{let t=new SkillTimeline();t.observe(cue,0);t.observe(cue,300);assert.equal(t.sample(300,false,false).phase,'AREA');assert.equal(t.sample(300,true,false).phase,'IMPACT');assert.equal(t.sample(300,false,true),null);assert.equal(validSkillCue({...cue,phases:[{phase:'DAMAGE',durationMs:-1}]}),false);});

test('nonadjacent command replay and panel remount never restart a cue',()=>{
 const t=new SkillTimeline();t.selectBattle('battle-1');t.observe(cue,0);
 const next={...cue,commandId:'00000000-0000-0000-0000-000000000002'};t.observe(next,200);
 t.observe(cue,400);assert.equal(t.sample(400,false,false).phase,'RELEASE');
 // Unmount/remount reads the same store-owned timeline, not a new animation start.
 t.selectBattle('battle-1');t.observe(next,900);assert.equal(t.sample(900,false,false),null);
 t.selectBattle('battle-2');assert.equal(t.sample(900,false,false),null);t.observe(cue,900);
 assert.equal(t.sample(900,false,false).phase,'CAST_START');
});
test('observed server phase durations are immutable and malformed input does not throw',()=>{
 const t=new SkillTimeline(),c=structuredClone(cue);t.observe(c,0);c.phases[0].durationMs=2000;
 assert.equal(t.sample(150,false,false).phase,'CHARGE');
 for(const invalid of [null,{}, {...cue,phases:null},{...cue,phases:[null,null,null,null,null,null]}])assert.equal(validSkillCue(invalid),false);
});
