import {CharacterAnimator} from '../../../src/animation/pilot';
import {AssetLoader} from '../../../src/animation/loader';
const manifest={species:'caplet',stage:1,canvas:{width:256,height:256},anchor:{x:.5,y:1},display:{width:82},animations:{idle:{frames:6,frameDuration:400,loop:true}}};
const loader=new AssetLoader({json:async()=>manifest,image:url=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve({width:image.width,height:image.height});image.onerror=reject;image.src=url;})});
const clip=await loader.loadRegistered('caplet',1,'/design/production-batches/monsters/idle-revision/M005/rigged/manifest.json','idle');
if(!clip) throw Error('Complete clip unavailable');
const animator=new CharacterAnimator();let paused=false,reduced=false,facing=1,elapsed=0,last=performance.now();
const sprite=document.querySelector<HTMLImageElement>('#sprite')!;
document.querySelector('#pause')!.addEventListener('click',()=>paused=!paused);
document.querySelector('#reduced')!.addEventListener('click',()=>reduced=!reduced);
document.querySelector('#facing')!.addEventListener('click',()=>{facing*=-1;sprite.style.transform=`scaleX(${facing})`;});
function tick(now:number){if(!paused)elapsed+=Math.min(100,now-last);last=now;const frame=animator.sample('caplet:idle',clip,elapsed,1,reduced);sprite.src=clip!.urls[frame];document.querySelector('#status')!.textContent=`Frame ${frame+1}/6 | paused=${paused} | reduced=${reduced}`;requestAnimationFrame(tick);}
requestAnimationFrame(tick);
