import { MonsterVisual } from './MonsterVisual';
import { useEntities } from '../stores/entities';
import { effectFor, damageFor } from '../presentation/model';
import { action } from '../overlay/bridge';
import { assets } from '../entities/assets';
import { CompanionVisual } from './CompanionVisual';
import type { CompanionState, Entity } from '../types/entity';
export function Creature({ kind, entity }: { kind:'moa'|'pip'; entity:Entity }) {
  const {visual,game}=useEntities();
  const effect=effectFor(visual?.phase,kind);const damage=damageFor(visual,kind);
  const defeated=kind==='pip' && game?.battle?.status==='VICTORY';
  return <div className={`creature gp-creature ${kind} ${entity.state}`} style={{'--skin':assets[kind].color,'--gp-direction':entity.facing} as React.CSSProperties}
    title={kind === 'moa' ? 'MOA · drag / click · right-click for server encounter' : 'PIP · click to interact'}
    onPointerDown={e => { if(e.button === 0 && kind === 'moa') void action('drag'); }}
    onClick={() => { if(kind === 'pip') void action('interact'); }}
    onContextMenu={e => { e.preventDefault(); void action('encounter'); }}>
      <div className={`gp-pose ${defeated?'gp-defeated':''}`}><div className={`gp-impulse gp-${effect}`}><div className={`gp-visual gp-${kind}`}>{kind === 'moa' ? <CompanionVisual state={entity.state as CompanionState} facing={entity.facing}/> : <MonsterVisual code="PIP" state={entity.state} facing={entity.facing}/>}</div></div></div>
      {effect==='capturing' && <span className="gp-capture-ring" aria-hidden="true"/>}
      {damage!=null && <span key={visual?.serial} className="gp-damage" aria-label={`Damage ${damage}`}>−{damage}</span>}
  </div>;
}
