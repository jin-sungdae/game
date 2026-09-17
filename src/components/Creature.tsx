import { action } from '../overlay/bridge';
import { assets } from '../entities/assets';
import { CompanionVisual, PlaceholderRenderer } from './CompanionVisual';
import type { CompanionState, Entity } from '../types/entity';
export function Creature({ kind, entity }: { kind:'moa'|'pip'; entity:Entity }) {
  return <div className={`creature ${kind} ${entity.state}`} style={{'--skin':assets[kind].color} as React.CSSProperties}
    title={kind === 'moa' ? 'MOA · drag / click · right-click to spawn PIP' : 'PIP · click to interact'}
    onPointerDown={e => { if(e.button === 0 && kind === 'moa') void action('drag'); }}
    onClick={() => { if(kind === 'pip') void action('interact'); }}
    onContextMenu={e => { e.preventDefault(); void action('spawn'); }}>
      <>{kind === 'moa' ? <CompanionVisual state={entity.state as CompanionState} facing={entity.facing}/> : <><PlaceholderRenderer facing={entity.facing}/><span className="name">{assets[kind].name}</span><span className="state">{entity.state}</span></>}</>
  </div>;
}
