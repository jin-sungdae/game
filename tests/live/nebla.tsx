// Read-only renderer harness for snapshots exported by the compiled World live test.
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {CompanionVisual} from '../../src/components/CompanionVisual';
import type {Snapshot} from '../../src/types/entity';
import {renderIdentity} from '../../src/presentation/evolution';
import '../../src/style.css';
import '../../src/presentation/gameplay.css';
import '../../src/presentation/baseMotion.css';
import '../../src/presentation/evolution.css';
const traces=await Promise.all(['nebla-natural.json','nebla-restored.json'].map(p=>fetch('./'+p).then(r=>r.json())));
const frames: {label:string;snapshot:Snapshot}[]=traces.flat();
function App(){
 const [index,setIndex]=useState(0),[facing,setFacing]=useState(1),[metrics,setMetrics]=useState(''),[motion,setMotion]=useState(false);
 const frame=frames[index],s=frame.snapshot,c=renderIdentity(s.identity,s.evolution)!;
 function measure(){
  const panel=document.querySelector('#panel')!,img=panel.querySelector('img')!;
  const p=panel.getBoundingClientRect(),r=img.getBoundingClientRect();
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;
  const ctx=canvas.getContext('2d')!;ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;
  let x0=256,y0=256,x1=-1,y1=-1;
  for(let y=0;y<256;y++)for(let x=0;x<256;x++)if(pixels[(y*256+x)*4+3]){x0=Math.min(x,x0);x1=Math.max(x,x1);y0=Math.min(y,y0);y1=Math.max(y,y1);}
  const left=facing===1?x0:256-x1-1,right=facing===1?x1+1:256-x0;
  setMetrics(JSON.stringify({frame:frame.label,source:img.getAttribute('src'),natural:[img.naturalWidth,img.naturalHeight],panel:[p.width,p.height],canvas:[r.x-p.x,r.y-p.y,r.width,r.height],anchor:[r.x-p.x+r.width/2,r.y-p.y+r.height],transform:getComputedStyle(img).transform,alphaPixels:[x0,y0,x1,y1],visible:[r.x-p.x+left*r.width/256,r.y-p.y+y0*r.height/256,r.x-p.x+right*r.width/256,r.y-p.y+(y1+1)*r.height/256]},null,2));
 }
 return <main style={{padding:24,height:'100%',overflow:'auto',background:'#eee'}}>
  {!motion&&<style>{'#panel *{animation:none!important;transition:none!important}'}</style>}
  <h1>NEBLA production validation</h1>
  <nav>{frames.map((f,i)=><button key={i} onClick={()=>{setIndex(i);setMetrics('')}}>{f.label}</button>)}<button onClick={()=>setFacing(1)}>RIGHT</button><button onClick={()=>setFacing(-1)}>LEFT</button><button onClick={measure}>Measure</button><button onClick={()=>setMotion(!motion)}>Motion {motion?'on':'off'}</button></nav>
  <p>World trace: {frame.label} / rendered identity: {c?.evolutionName} / phase: {s.evolution!.phase}</p>
  <div id="panel" style={{width:96,height:104,overflow:'hidden',outline:'1px solid red',position:'relative',marginTop:24}}>
   <div className="creature gp-creature moa"><div className="gp-pose"><div className="gp-impulse gp-none"><div className="gp-visual gp-moa"><div className={`evolution-pose evo-${s.evolution!.phase}`}>
    <CompanionVisual species={c.species.toLowerCase()} evolutionStage={c.evolutionStage} displayName={c.evolutionName} state="IDLE" facing={facing}/>
   </div></div></div></div></div>
  </div><pre>{metrics}</pre>
 </main>
}
createRoot(document.getElementById('root')!).render(<App/>);
