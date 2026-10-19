import React,{useState,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {MonsterVisual} from '../../../src/components/MonsterVisual';
import trace from './native-trace.json';
import '../../../src/animation/character.css';
function App(){const [index,setIndex]=useState(0);const [paused,setPaused]=useState(false);
useEffect(()=>{if(paused)return;const timer=setInterval(()=>setIndex(i=>Math.min(trace.length-1,i+1)),50);return()=>clearInterval(timer);},[paused]);
const row=trace[index];const prev=trace[Math.max(0,index-1)];const speed=Math.hypot(row.x-prev.x,row.y-prev.y)/.05;
return <><h1>CAPLET Native World trace → registered Renderer</h1><p>Rust test fixture only. Production spawn remains disabled.</p><button onClick={()=>setIndex(0)}>Replay</button><button onClick={()=>setPaused(!paused)}>Pause / Resume</button><p>{row.state} | native t={row.time.toFixed(2)} | x={row.x.toFixed(2)} y={row.y.toFixed(2)} facing={row.facing}</p><div style={{width:256,height:256,position:'relative',border:'1px solid white',transform:`translate(${row.x-trace[0].x}px,${row.y-trace[0].y}px)`}}><MonsterVisual code="CAPLET" state={row.state} facing={row.facing} entityId="native-trace-caplet" animationInput={{state:row.state,speed,suppressed:paused}}/></div></>}
createRoot(document.getElementById('root')!).render(<App/>);
