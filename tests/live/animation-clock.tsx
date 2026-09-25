// Opt-in real-browser StrictMode integration; never imported by production entrypoint.
import React,{StrictMode,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {CharacterRenderer} from '../../src/components/CharacterRenderer';
import {pilotDefinition} from '../../src/animation/pilot';
import '../../src/style.css';
import '../../src/animation/character.css';
const pending=new Set<number>();let maximum=0,setups=0,cleanups=0;
const nativeRequest=window.requestAnimationFrame.bind(window),nativeCancel=window.cancelAnimationFrame.bind(window);
window.requestAnimationFrame=callback=>{const id=nativeRequest(time=>{pending.delete(id);callback(time);});pending.add(id);maximum=Math.max(maximum,pending.size);return id;};
window.cancelAnimationFrame=id=>{pending.delete(id);nativeCancel(id);};
function Character({index}:{index:number}) {
  useEffect(()=>{setups++;return ()=>{cleanups++;};},[]);
  return <div style={{width:96,height:104}}><CharacterRenderer pilot={pilotDefinition(index%2?'PIP':'moa')!} input={{speed:index%2?40:0,state:index%2?'ROAMING':'IDLE',suppressed:false}} facing={1} name={index%2?'PIP':'MOA'} entityId={`strict-${index}`}/></div>;
}
const root=createRoot(document.getElementById('clock-test')!);
const wait=()=>new Promise(resolve=>setTimeout(resolve,80));
const checks:boolean[]=[];
try {
  for(let cycle=0;cycle<20;cycle++){
    root.render(<StrictMode><div key={cycle}>{Array.from({length:16},(_,index)=><Character key={index} index={index}/>)}</div></StrictMode>);
    await wait();checks.push(pending.size===1,document.querySelectorAll('.character-renderer').length===16);
    root.render(null);await wait();checks.push(pending.size===0);
  }
  root.unmount();await wait();
  const result={status:checks.every(Boolean)&&maximum===1&&pending.size===0&&setups===640&&cleanups===640?'PASS':'FAIL',cycles:20,characters:16,maximumPendingRAF:maximum,pendingAfterCleanup:pending.size,setups,cleanups,checks};
  document.getElementById('result')!.textContent=JSON.stringify(result);
} finally {window.requestAnimationFrame=nativeRequest;window.cancelAnimationFrame=nativeCancel;}
