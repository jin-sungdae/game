const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {baseMotion}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'presentation/baseMotion.js'));
const css=fs.readFileSync('src/presentation/baseMotion.css','utf8');
const base=fs.readFileSync('src/components/BaseVisual.tsx','utf8');
const companion=fs.readFileSync('src/components/CompanionVisual.tsx','utf8');
const monster=fs.readFileSync('src/components/MonsterVisual.tsx','utf8');
const creature=fs.readFileSync('src/components/Creature.tsx','utf8');
for(const [state,motion] of Object.entries({IDLE:'idle',WALKING:'walk',LOOKING:'look',SITTING:'sit',SLEEPING:'sleep',REACTING:'react',DRAGGING:'still'})) {
 test(`MOA ${state} presentation`,()=>{
  assert.equal(baseMotion('moa',state).className,`base-motion bm-moa-${motion}`);
  assert.equal(baseMotion('moa',state).sleep,state==='SLEEPING');
 });
}
for(const [state,motion] of Object.entries({SPAWNING:'idle',ENGAGED:'idle',ROAMING:'walk',DESPAWNING:'still'}))
 test(`PIP ${state} presentation`,()=>assert.equal(baseMotion('pip',state).className,`base-motion bm-pip-${motion}`));
test('unknown states/species are still, without new domain behavior',()=>{
 for(const [species,state] of [['moa','constructor'],['pip','unknown'],['ruu','IDLE']]) assert.match(baseMotion(species,state).className,/-still$/);
});
test('same snapshot keeps class and existing nodes; state transitions only change presentation',()=>{
 const first=baseMotion('moa','IDLE');for(let i=0;i<100;i++)assert.deepEqual(baseMotion('moa','IDLE'),first);
 assert.notDeepEqual(baseMotion('moa','WALKING'),first);assert.deepEqual(baseMotion('moa','IDLE'),first);
 for(const source of [base,companion,monster])assert.doesNotMatch(source,/\bkey=|setInterval|requestAnimationFrame/);
 assert.doesNotMatch(base.slice(base.indexOf('export function BaseSprite')),/useEffect|useState|AnimationController/);
});
test('only base branch receives motion; frame and CSS fallback retain existing priority',()=>{
 assert.match(companion,/sprite && size \? <img[\s\S]+source.kind==='base' \? <BaseSprite[\s\S]+PlaceholderRenderer/);
 assert.match(monster,/source.kind==='animation' \? <img[\s\S]+source.kind==='base' \? <BaseSprite[\s\S]+PlaceholderRenderer/);
 assert.doesNotMatch(companion,/className=\{motion/);
 assert.match(base,/className=\{motion.className\}[\s\S]*<img/);
});
test('facing belongs to image; base and gameplay transforms use different nodes',()=>{
 assert.match(base,/<div className=\{motion.className\}[\s\S]*<img[\s\S]*scaleX\(\$\{directionScale\(facing\)\}/);
 assert.match(css,/\.base-motion\{[^}]*transform-origin:50% 100%/);
 assert.match(creature,/gp-pose[\s\S]*gp-impulse[\s\S]*gp-visual[\s\S]*CompanionVisual/);
 for(const effect of ['attack','hit','capturing','capture-success','capture-fail','defeated']) assert.ok(css.includes(`.gp-${effect} .base-motion`));
 assert.match(css,/\.gp-defeated \.base-motion,[^{]+\{animation:none;transform:none\}/);
});
test('defeat stays server-authoritative; capture retains existing pipeline',()=>{
 assert.match(creature,/kind==='pip' && game\?\.battle\?\.status==='VICTORY'/);
 assert.doesNotMatch(base,/CAPTURED|VICTORY|action\(/);
});
test('reduced motion removes presentation only; sleep indicator remains static in canvas',()=>{
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)\{\.base-motion\{animation:none!important;transform:none!important\}/);
 assert.match(css,/\.base-sleep\{[^}]*top:4px;right:8px/);
 assert.match(base,/motion.sleep && <span className="base-sleep"/);
 assert.doesNotMatch(css,/will-change|position:fixed/);
});
test('cadence and transforms remain subtle; no CSS world position animation',()=>{
 assert.match(css,/bm-breathe 2\.6s/);assert.match(css,/bm-walk \.48s/);assert.match(css,/bm-scamper \.34s/);
 assert.match(css,/bm-sleep 4\.6s/);assert.match(css,/bm-react \.32s ease-out both/);
 assert.doesNotMatch(css,/@keyframes[^}]*\{[^}]*\b(left|right|top|bottom):/);
});
