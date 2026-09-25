import { spawnPresentation } from '../presentation/spawn';
import { evolutionModel, renderIdentity } from '../presentation/evolution';
import { MonsterVisual } from './MonsterVisual';
import { useEntities } from '../stores/entities';
import { effectFor, damageFor } from '../presentation/model';
import { action } from '../overlay/bridge';
import { assets } from '../entities/assets';
import { CompanionVisual } from './CompanionVisual';
import type { CompanionState, Entity } from '../types/entity';
export function Creature({ kind, entity }: { kind:'moa'|'pip'; entity:Entity }) {
  const {visual,game,identity,evolution,monster,bond,animation}=useEntities();
  const companion=renderIdentity(identity,evolution);
  const evo=evolutionModel(evolution,game?.busy);
  const effect=effectFor(visual?.phase,kind);const damage=damageFor(visual,kind);
  const arrival=kind==='pip' ? spawnPresentation(monster?.rarity,entity.state,Boolean(game?.battle)||Boolean(game?.busy)||effect!=='none') : null;
  const defeated=kind==='pip' && game?.battle?.status==='VICTORY';
  const animationInput={state:entity.state,speed:animation?.[kind]??0,suppressed:Boolean(arrival)||entity.state==='SPAWNING'||entity.state==='DESPAWNING'||Boolean(game?.battle)||Boolean(game?.busy)||effect!=='none'||(evolution?.phase??'IDLE')!=='IDLE'};
  return <div className={`creature gp-creature ${kind} ${entity.state} ${arrival?'spawn-enhanced':''}`} style={{'--skin':assets[kind].color,'--gp-direction':entity.facing} as React.CSSProperties}
    title={kind === 'moa' ? `${identity?.evolutionName ?? 'MOA'} · drag / click · right-click for server encounter` : `${monster?.monsterCode ?? 'Debug PIP'} · click to interact`}
    onPointerDown={e => { if(e.button === 0 && kind === 'moa') void action('drag'); }}
    onClick={() => { if(kind === 'pip') void action('interact'); }}
    onContextMenu={e => { e.preventDefault(); void action('encounter'); }}>
      {arrival && <span className={`spawn-highlight spawn-${arrival.tier}`} style={{'--spawn-duration':`${arrival.duration}ms`} as React.CSSProperties} aria-hidden="true"/>}
      <div className={`gp-pose ${defeated?'gp-defeated':''}`}><div className={`gp-impulse gp-${effect}`}><div className={`gp-visual gp-${kind}`}>{kind === 'moa' ? <div className={`evolution-pose evo-${evolution?.phase ?? 'IDLE'}`}><CompanionVisual animationInput={animationInput} entityId={`companion:${identity?.playerCompanionId??0}:${companion?.evolutionStage??1}`} species={companion?.species.toLowerCase() ?? 'moa'} evolutionStage={companion?.evolutionStage ?? 1} displayName={companion?.evolutionName} state={entity.state as CompanionState} facing={entity.facing}/></div> : <MonsterVisual animationInput={animationInput} entityId={monster?.encounterId??'debug-pip'} code={monster?.monsterCode ?? "PIP"} state={entity.state} facing={entity.facing}/>}</div></div></div>
      {kind==='moa' && <button className={`evolution-entry ${evo.available?'available':''}`} aria-label={evo.available?'Evolution available':'Companion evolution'} title={evo.available?'Evolution Available':'Companion evolution'} onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();void action('evolution');}} onContextMenu={e=>{e.preventDefault();e.stopPropagation();}}>✦</button>}
      {kind==='moa' && bond?.feedback && <span className="bond-feedback" role="status">{bond.feedback}</span>}
      {effect==='capturing'  && <span className="gp-capture-ring" aria-hidden="true"/>}
      {damage!=null && <span key={visual?.serial} className="gp-damage" aria-label={`Damage ${damage}`}>−{damage}</span>}
  </div>;
}
