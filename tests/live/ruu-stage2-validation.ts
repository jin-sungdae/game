import {AnimationController} from '../../src/animation/controller';
import {animationClock} from '../../src/animation/clock';
import {parseManifest,frameUrls} from '../../src/animation/model';
const base='/design/creature-production-v3/ruu/stage02';
const root=document.getElementById('root')!;
root.innerHTML='<h1>RUU Stage 2 — VALIDATION_FAILED</h1><p>Diagnostic playback only. Not Production registration or native GUI acceptance.</p><select id="version"><option>raw</option><option>repair-v2</option><option selected>rebuild-v3</option></select> <button id="pause">Pause</button> <button id="next">Next frame</button> <button id="background">Change background</button><p id="status"></p><div id="canvas" style="width:256px;height:256px;background:#202020;border:1px solid red"><img id="frame" width="256" height="256" style="display:block"></div>';
const img=document.getElementById('frame') as HTMLImageElement,select=document.getElementById('version') as HTMLSelectElement,status=document.getElementById('status')!;
let stop=()=>{},urls:string[]=[],frame=0,running=true;const controller=new AnimationController();
function show(index:number){frame=index;img.src=urls[index];status.textContent=`${select.value} frame ${index}/7 — candidate only`;}
function resume(){stop();stop=animationClock.subscribe(()=>show(controller.sample().frame));}
async function load(){stop();const dir=`${base}/${select.value}`,manifest=parseManifest(await fetch(dir+'/manifest.json').then(r=>r.json()),'ruu',2);urls=frameUrls(dir,'idle',manifest.animations.idle);await Promise.all(urls.map(url=>new Promise<void>((resolve,reject)=>{const image=new Image();image.onload=()=>resolve();image.onerror=()=>reject(Error(url));image.src=url;})));controller.select(select.value,manifest.animations.idle);show(0);if(running)resume();}
select.onchange=()=>void load();
document.getElementById('pause')!.onclick=()=>{running=!running;document.getElementById('pause')!.textContent=running?'Pause':'Play';if(running)resume();else stop();};
document.getElementById('next')!.onclick=()=>{running=false;stop();document.getElementById('pause')!.textContent='Play';show((frame+1)%8);};
let light=false;document.getElementById('background')!.onclick=()=>{light=!light;document.getElementById('canvas')!.style.background=light?'#eeeeee':'#202020';};
window.addEventListener('pagehide',()=>stop());
void load();
