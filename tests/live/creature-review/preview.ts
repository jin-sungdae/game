import catalog from './catalog.json';
import {CharacterAnimator} from '../../../src/animation/pilot';
import {AssetLoader} from '../../../src/animation/loader';
import type {LoadedClip} from '../../../src/animation/loader';
const select=document.querySelector<HTMLSelectElement>('#creature')!;
const animation=document.querySelector<HTMLSelectElement>('#animation')!;
const section=document.querySelector<HTMLElement>('#clips')!;
const summary=document.querySelector<HTMLElement>('#summary')!;
for(const row of catalog.creatures){const o=document.createElement('option');o.value=row.id;o.textContent=`${row.id} — 후보 ${row.clips.length}개`;select.append(o);}
const totals=catalog.coverageSummary;
document.querySelector('#totals')!.textContent=`전체 ${totals.creatures} Creature · 완료 ${totals.completeActions}/${totals.requiredActions} 행동 · 전체 완료 ${totals.completeCreatures}/${totals.creatures} · 기존 30종은 Concept ID와 별도 집계`;
select.value='M005';let paused=false,reduced=false,elapsed=0,last=performance.now(),generation=0;
let views:{image:HTMLImageElement;status:HTMLElement;clip:LoadedClip;animator:CharacterAnimator;key:string;bounds:number[][]}[]=[];
async function show(){const current=++generation;views=[];section.replaceChildren();elapsed=0;
 const row=catalog.creatures.find(r=>r.id===select.value)!;
 const c=row.coverage;
 summary.textContent=`${row.productionStatus} · 완료 ${c.completeActions}/${c.requiredActions} · Ledger Runtime ${c.recordedRuntimeActions} · 실제 Manifest 파일 세트 ${c.manifestFileSetsPresent} · 후보 행동 ${c.candidateActions} (자동 PNG 통과 ${c.automatedCandidateActions}) · 미공급 ${c.missingFrameSetActions} · 실패 ${c.validationFailedActions} · GUI 대기 ${c.guiPendingActions} · 자동 검사와 파일 존재는 Production 승인·Native GUI 증거가 아닙니다.`;
 for(const action of row.actions){
  if(!('recoveryPath' in action) || typeof action.recoveryPath!=='string')continue;
  const article=document.createElement('article');article.dataset.action=action.action.toLowerCase();
  const title=document.createElement('h2');title.textContent=`${action.action} — 실패 보존 Keypose (재생·등록 차단)`;
  const image=document.createElement('img');image.src='/'+action.recoveryPath;image.alt=`${row.id} ${action.action} failed recovery`;
  const reason=document.createElement('p');reason.textContent='blockReason' in action ? String(action.blockReason) : 'VALIDATION_FAILED';
  article.append(title,image,reason);section.append(article);
 }
 if(!row.clips.length){const empty=document.createElement('p');empty.textContent='보존된 rigged 후보가 없습니다. 기존 Ledger의 미공급·실패 상태를 유지합니다.';section.append(empty);animation.replaceChildren(new Option('전체 Animation','all'));return;}
 animation.replaceChildren(new Option('전체 Animation','all'),...Array.from(new Set([...row.clips.map(c=>c.action),...row.actions.filter(a=>'recoveryPath' in a).map(a=>a.action.toLowerCase())])).map(a=>new Option(a.toUpperCase(),a)));
 for(const [n,c] of row.clips.entries()){
  const article=document.createElement('article');article.dataset.action=c.action;const title=document.createElement('h2');title.textContent=`${c.action.toUpperCase()} / ${n+1}`;
  const note=document.createElement('small');note.textContent=`PNG 자동 검사 ${c.automated} · ${c.frameCount}프레임 · ${c.artwork}`;
  const details=document.createElement('pre');details.textContent=c.directory+'\n'+c.timingSource+'\n'+c.errors.join('\n');article.append(title,note,details);section.append(article);
  if(c.automated!=='PASS')continue;
  const image=document.createElement('img');image.alt=`${row.id} ${c.action} candidate`;const status=document.createElement('p');const pair=document.createElement('div');pair.className='comparison';
  if(row.basePath){const base=document.createElement('img');base.src=row.basePath;base.alt=`${row.id} BASE`;const label=document.createElement('figure');label.append(base);const caption=document.createElement('figcaption');caption.textContent='기존 BASE (원본 유지)';label.append(caption);pair.append(label);}
  const candidate=document.createElement('figure');candidate.append(image);const caption=document.createElement('figcaption');caption.textContent='후보 · 동일 256px Canvas / bottom-center 기준선';candidate.append(caption);pair.append(candidate);article.append(pair,status);
  const approval=document.createElement('p');const action=row.actions.find(a=>a.action.toLowerCase()===c.action);approval.textContent=`Ledger: ${action?.animationStatus ?? 'NOT_VERIFIED'} / Runtime: ${action?.runtimeStatus ?? 'NOT_VERIFIED'} / GUI: ${action?.guiStatus ?? 'NOT_VERIFIED'} · 후보 외형·자연스러움 별도 검토 필요 · ${action && 'blockReason' in action ? action.blockReason : ''}`;article.append(approval);
  const manifest={species:'review',stage:1,canvas:{width:256,height:256},anchor:{x:.5,y:1},display:{width:256},animations:{[c.action]:{frames:c.frameCount,frameDuration:c.frameDuration,loop:true}}};
  const loader=new AssetLoader({json:async()=>manifest,image:url=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve({width:img.naturalWidth,height:img.naturalHeight});img.onerror=reject;img.src=url;})});
  const clip=await loader.loadRegistered('review',1,c.directory.slice(0,c.directory.lastIndexOf('/'))+'/manifest.json',c.action);
  if(current!==generation)return;
  if(clip)views.push({image,status,clip,animator:new CharacterAnimator(),key:c.directory,bounds:c.bounds});else status.textContent='이미지 로딩 실패 — 재생 차단';
 }
}
animation.addEventListener('change',()=>{for(const card of section.querySelectorAll<HTMLElement>('article'))card.hidden=animation.value!=='all'&&card.dataset.action!==animation.value;});
select.addEventListener('change',()=>void show());document.querySelector('#pause')!.addEventListener('click',()=>paused=!paused);document.querySelector('#reduced')!.addEventListener('click',()=>reduced=!reduced);
function tick(now:number){if(!paused)elapsed+=Math.min(100,now-last);last=now;for(const v of views){const f=v.animator.sample(v.key,v.clip,elapsed,1,reduced);v.image.src=v.clip.urls[f];v.status.textContent=`Frame ${f+1}/${v.clip.clip.frames} · paused=${paused} · reduced=${reduced} · Alpha Bounds [${v.bounds[f]?.join(', ')}] · Canvas Anchor (128,256)`;}requestAnimationFrame(tick);}
void show();requestAnimationFrame(tick);
