import { action } from '../overlay/bridge';
import { useEntities } from '../stores/entities';
export function Interaction() {
 const {game:g}=useEntities();const b=g?.battle;const active=b?.encounterStatus==='ACTIVE';
 return <div className="interaction"><strong>PIP {g?.monsterLevel ? `Lv.${g.monsterLevel}` : 'DEBUG'}</strong>
 {b && <><span>{b.status} · Turn {b.turn}</span><label>PIP {b.monster.hp}/{b.monster.maxHp}<progress value={b.monster.hp} max={b.monster.maxHp}/></label><label>MOA {b.companion.hp}/{b.companion.maxHp}<progress value={b.companion.hp} max={b.companion.maxHp}/></label></>}
 {g?.feedback && <small role="status">{g.feedback}</small>}
 {b?.reward && <small>Gold +{b.reward.gold} · EXP +{b.reward.exp} · Bond +{b.reward.bond}</small>}
 {g?.error && <small role="alert">{g.error} — 상태 확인 후 다시 시도하세요.</small>}
 <div className="actions">
 {!b && g?.encounterId && <button disabled={g.busy} onClick={()=>void action('battle')}>Battle</button>}
 {active && <><button disabled={g?.busy||b?.status!=='ACTIVE'} onClick={()=>void action('attack')}>ATTACK</button><button disabled={g?.busy} onClick={()=>void action('capture')}>CAPTURE</button><button disabled={g?.busy} onClick={()=>void action('ignore')}>IGNORE</button></>}
 {b && <button disabled={g?.busy} onClick={()=>void action('refresh')}>Refresh</button>}
 <button disabled={g?.busy} onClick={()=>void action('collection')}>Collection</button><button onClick={()=>void action('close')}>Close</button>
 </div>{g?.busy && <small>Loading…</small>}{g?.collection.map(c=><small key={c.monsterCode}>{c.monsterCode} × {c.captureCount}</small>)}</div>;
}
