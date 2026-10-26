import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MonsterVisual} from '../../../src/components/MonsterVisual';
import '../../../src/animation/character.css';
function App(){const [state,setState]=useState('SLEEPING');const [paused,setPaused]=useState(false);const [facing,setFacing]=useState(1);return <><h1>CAPLET registered SLEEP Runtime</h1><p>Production renderer with controlled input. Native spawn is not enabled.</p><button onClick={()=>setState(state==='SLEEPING'?'IDLE':'SLEEPING')}>Sleep / Wake</button><button onClick={()=>setPaused(!paused)}>Pause / Resume</button><button onClick={()=>setFacing(-facing)}>Facing</button><div style={{width:256,height:256,position:'relative',border:'1px solid white'}}><MonsterVisual code="CAPLET" state={state} facing={facing} entityId="caplet-validation" animationInput={{state,speed:0,suppressed:paused}}/></div></>}
createRoot(document.getElementById('root')!).render(<App/>);
