import { EvolutionInteraction } from './EvolutionInteraction';
import { action } from '../overlay/bridge';
import { useEntities } from '../stores/entities';
import { hpModel } from '../presentation/model';
function HpBar({name,hp,max}:{name:string;hp:number;max:number}) {
 const h=hpModel(hp,max);
 return <div className={`gp-hp gp-${h.tone}`}><div className="gp-hp-label"><span>{name} · {h.tone}</span><b>{h.text}</b></div><div className="gp-hp-track" role="progressbar" aria-label={`${name} HP`} aria-valuenow={hp} aria-valuemin={0} aria-valuemax={max}><span style={{width:`${h.percent}%`}}/></div></div>;
}
export function Interaction() {
 const {game:g,visual:v,interaction,evolution,identity}=useEntities();
 if(interaction==='EVOLUTION') return <EvolutionInteraction view={evolution} gameBusy={g?.busy}/>;const b=g?.battle;const active=b?.encounterStatus==='ACTIVE';
 const result=v?.phase==='CAPTURE_SUCCESS'?'Captured!':v?.phase==='CAPTURE_FAIL'?'Capture failed':b?.status==='VICTORY'?(active?'PIP defeated · Capture opportunity':'Battle complete'):b?.status==='DEFEAT'?'MOA needs a rest':b?.encounterStatus==='CAPTURED'?'Added to Collection':b?.status??'A small encounter';
 return <section className="interaction gp-panel" aria-label="PIP encounter">
 <header className="gp-header"><div><small>WILD ENCOUNTER</small><strong>PIP <span>{g?.monsterLevel?`Lv.${g.monsterLevel}`:'DEBUG'}</span></strong></div><button className="gp-close" aria-label="Close panel" onClick={()=>void action('close')}>×</button></header>
 {b && <><HpBar name="PIP" hp={b.monster.hp} max={b.monster.maxHp}/><HpBar name={identity?.evolutionName ?? "MOA"} hp={b.companion.hp} max={b.companion.maxHp}/></>}
 <p className="gp-status" role="status">{g?.busy?(v?.phase==='CAPTURING'?'Capturing…':'Connecting…'):result}</p>
 {g?.error && <p className="gp-error" role="alert">{g.error}. Refresh to check the result.</p>}
 <div className="gp-actions">
 {!b&&g?.encounterId&&<button disabled={g.busy} onClick={()=>void action('battle')}>Start battle</button>}
 {active&&<><button className="gp-primary" disabled={g?.busy||b?.status!=='ACTIVE'} onClick={()=>void action('attack')}>ATTACK</button><button className="gp-capture-button" disabled={g?.busy} onClick={()=>void action('capture')}>CAPTURE</button><button className="gp-quiet" disabled={g?.busy} onClick={()=>void action('ignore')}>Ignore</button></>}
 {b&&<button className="gp-quiet" disabled={g?.busy} onClick={()=>void action('refresh')}>Refresh</button>}
 <button className="gp-quiet" disabled={g?.busy} onClick={()=>void action('collection')}>Collection</button>
 </div>
 {g?.captureChance!=null&&<small className="gp-note">Last server capture chance: {Math.round(g.captureChance*100)}%</small>}
 {v?.phase==='REWARD'&&v.reward&&<div key={v.serial} className="gp-toast" role="status">+{v.reward.gold} Gold · +{v.reward.exp} EXP · +{v.reward.bond} Bond</div>}
 {v?.phase==='LEVEL_UP'&&v.level&&<div key={v.serial} className="gp-toast" role="status">LEVEL UP · Lv.{v.level.from} → Lv.{v.level.to}</div>}
 {g?.collection.map(c=><small className="gp-collection" key={c.monsterCode}>{c.monsterCode} · Collected ×{c.captureCount}</small>)}
 </section>;
}
