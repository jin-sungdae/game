import catalog from './catalog.json';
import {CharacterAnimator} from '../../../src/animation/pilot';
import {AssetLoader} from '../../../src/animation/loader';
import type {LoadedClip} from '../../../src/animation/loader';
const select=document.querySelector<HTMLSelectElement>('#creature')!;
const section=document.querySelector<HTMLElement>('#clips')!;
const summary=document.querySelector<HTMLElement>('#summary')!;
for(const row of catalog.creatures){const o=document.createElement('option');o.value=row.id;o.textContent=`${row.id} — 후보 ${row.clips.length}개`;select.append(o);}
select.value='M005';let paused=false,reduced=false,elapsed=0,last=performance.now(),generation=0;
let views:{image:HTMLImageElement;status:HTMLElement;clip:LoadedClip;animator:CharacterAnimator;key:string}[]=[];
async function show(){const current=++generation;views=[];section.replaceChildren();elapsed=0;
 const row=catalog.creatures.find(r=>r.id===select.value)!;
 summary.textContent=`${row.productionStatus} · 실제 연결 완료 행동 ${row.actions.filter(a=>a.runtimeStatus==='RUNTIME_CONNECTED').length}개 · 후보 자동 검사는 최종 Artwork 승인이 아닙니다.`;
 if(!row.clips.length){section.textContent='보존된 rigged 후보가 없습니다. 기존 Ledger의 미공급·실패 상태를 유지합니다.';return;}
 for(const [n,c] of row.clips.entries()){
  const article=document.createElement('article');const title=document.createElement('h2');title.textContent=`${c.action.toUpperCase()} / ${n+1}`;
  const note=document.createElement('small');note.textContent=`${c.automated} · ${c.frameCount}프레임 · ${c.artwork}`;
  const details=document.createElement('pre');details.textContent=c.directory+'\n'+c.timingSource+'\n'+c.errors.join('\n');article.append(title,note,details);section.append(article);
  if(c.automated!=='PASS')continue;
  const image=document.createElement('img');image.alt=`${row.id} ${c.action} candidate`;const status=document.createElement('p');article.append(image,status);
  const manifest={species:'review',stage:1,canvas:{width:256,height:256},anchor:{x:.5,y:1},display:{width:256},animations:{[c.action]:{frames:c.frameCount,frameDuration:c.frameDuration,loop:true}}};
  const loader=new AssetLoader({json:async()=>manifest,image:url=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve({width:img.naturalWidth,height:img.naturalHeight});img.onerror=reject;img.src=url;})});
  const clip=await loader.loadRegistered('review',1,c.directory.slice(0,c.directory.lastIndexOf('/'))+'/manifest.json',c.action);
  if(current!==generation)return;
  if(clip)views.push({image,status,clip,animator:new CharacterAnimator(),key:c.directory});else status.textContent='이미지 로딩 실패 — 재생 차단';
 }
}
select.addEventListener('change',()=>void show());document.querySelector('#pause')!.addEventListener('click',()=>paused=!paused);document.querySelector('#reduced')!.addEventListener('click',()=>reduced=!reduced);
function tick(now:number){if(!paused)elapsed+=Math.min(100,now-last);last=now;for(const v of views){const f=v.animator.sample(v.key,v.clip,elapsed,1,reduced);v.image.src=v.clip.urls[f];v.status.textContent=`Frame ${f+1}/${v.clip.clip.frames} · paused=${paused} · reduced=${reduced}`;}requestAnimationFrame(tick);}
void show();requestAnimationFrame(tick);
