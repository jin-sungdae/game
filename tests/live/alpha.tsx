// Read-only production-renderer build consuming actual compiled World snapshots.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {CompanionVisual} from '../../src/components/CompanionVisual';
import {renderIdentity,evolutionModel} from '../../src/presentation/evolution';
import {collectionDexModel} from '../../src/presentation/collectionDex';
import type {Snapshot} from '../../src/types/entity';
import '../../src/style.css';
import '../../src/presentation/gameplay.css';
import '../../src/presentation/baseMotion.css';
import '../../src/presentation/evolution.css';
async function start(){
const groups=await Promise.all(['fresh','progress','restored'].map(p=>fetch(`/evidence/frames-${p}.json`).then(r=>r.json())));
const frames:{label:string;snapshot:Snapshot}[]=groups.flat();
function App(){return <main style={{padding:20,height:'100%',overflow:'auto',background:'#edf4ef',color:'#142d21'}}>
 <h1>LUMA Alpha — actual World snapshots</h1>
 <p>Production renderer; recorded server state. No gameplay controls or mutations.</p>
 <style>{'.audit-panel *{animation:none!important;transition:none!important}'}</style>
 <div style={{display:'flex',flexWrap:'wrap',gap:20}}>{frames.map(({label,snapshot:s})=>{
  const c=renderIdentity(s.identity,s.evolution)!;const dex=collectionDexModel(s.dex);const evo=evolutionModel(s.evolution);
  return <article key={label} data-frame={label} data-rendered-stage={c.evolutionStage} style={{width:260,padding:12,border:'1px solid #72947c'}}>
   <h2>{label}</h2><p>{c.evolutionName} · Stage{c.evolutionStage} · phase {s.evolution?.phase}</p>
   <div className="audit-panel" style={{width:96,height:104,position:'relative',overflow:'hidden',outline:'1px solid #aaa'}}>
    <div className="creature gp-creature moa"><div className="gp-pose"><div className="gp-impulse gp-none"><div className="gp-visual gp-moa">
    <CompanionVisual species={c.species.toLowerCase()} evolutionStage={c.evolutionStage} displayName={c.evolutionName} state="IDLE" facing={1}/>
    </div></div></div></div>
   </div>
   <p>Lv{s.identity?.level} / EXP{s.identity?.exp} / Bond{s.identity?.bond} / Gold{s.items?.inventory?.gold}</p>
   <p>Evolution available: {String(evo.available)} / Dex {dex.discovered} discovered, {dex.captured} captured</p>
   <ul>{dex.slots.slice(0,15).map(slot=><li key={slot.dexNo} data-dex-state={slot.state}>{slot.dexNo}: {slot.name} · {slot.state}</li>)}</ul>
  </article>;
 })}</div>
</main>}
createRoot(document.getElementById('root')!).render(<App/>);

}
void start();
