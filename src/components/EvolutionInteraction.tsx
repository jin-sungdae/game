import { action } from '../overlay/bridge';
import { evolutionModel } from '../presentation/evolution';
import type { EvolutionPresentation } from '../types/entity';
export function EvolutionInteraction({view,gameBusy}:{view?:EvolutionPresentation;gameBusy?:boolean}) {
  const model=evolutionModel(view,gameBusy);const r=view?.eligibility?.requirements;
  return <section className="interaction gp-panel" aria-label="Companion evolution">
    <header className="gp-header"><div><small>COMPANION EVOLUTION</small><strong>{model.title}</strong></div></header>
    {r && <div className="evolution-requirements"><p>Lv.{r.level.current} / {r.level.required} {r.level.met?'✓':''}</p><p>Bond {r.bond.current} / {r.bond.required} {r.bond.met?'✓':''}</p></div>}
    <p role={view?.error?'alert':'status'}>{model.message}</p>
    <div className="gp-actions"><button disabled={!model.canEvolve} onClick={()=>void action('evolve')}>EVOLVE</button><button onClick={()=>void action('close')}>LATER</button></div>
    <div className="gp-actions"><button disabled={gameBusy} onClick={()=>void action('inventory')}>Inventory</button><button disabled={gameBusy} onClick={()=>void action('shop')}>Shop</button></div>
    <button disabled={gameBusy} onClick={()=>void action('dex')}>DEX</button>
    <small>진화는 명시적으로 선택할 때만 진행됩니다.</small>
  </section>;
}
