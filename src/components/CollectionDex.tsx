import { useState } from 'react';
import { action } from '../overlay/bridge';
import { useBaseAsset } from '../assets/useBaseAsset';
import { collectionDexModel, dexFilters, type DexFilter, type CollectionSlot } from '../presentation/collectionDex';
import type { CollectionDexPresentation } from '../types/entity';
function DexArt({slot}:{slot:CollectionSlot}) {
  const base = useBaseAsset(slot.asset);
  return <div className="dex-art" aria-hidden="true">
    {base.url ? <img src={base.url} alt="" draggable={false} onError={base.fail}/> : <span className="dex-silhouette">?</span>}
  </div>;
}
export function CollectionDex({view,otherBusy=false}:{view?:CollectionDexPresentation;otherBusy?:boolean}) {
  const [filter,setFilter] = useState<DexFilter>('ALL');
  const model = collectionDexModel(view,filter);
  return <section className="interaction gp-panel dex-panel" aria-label="LUMA DEX">
    <header className="gp-header"><strong>LUMA DEX</strong><button aria-label="Close Dex" onClick={()=>void action('close')}>×</button></header>
    <div className="dex-counts"><span>Discovered {model.discovered ?? '—'} / {model.total}</span><span>Captured {model.captured ?? '—'} / {model.total}</span></div>
    <div className="dex-filters" role="group" aria-label="Rarity filter">{dexFilters.map(value=><button key={value} aria-pressed={filter===value} onClick={()=>setFilter(value)}>{value}</button>)}</div>
    <div className="dex-toolbar"><button disabled={model.busy||otherBusy} onClick={()=>void action('dex-refresh')}>Refresh</button><small>발견·포획 기록은 서버에 저장됩니다</small></div>
    <p className="dex-status" role={model.error?'alert':'status'}>{model.message}</p>
    <ol className="dex-list" aria-label="Monster Dex slots" aria-busy={model.busy}>
      {model.slots.map(slot=><li className="dex-slot" key={slot.dexNo}>
        <DexArt slot={slot}/><div className="dex-details"><small>No. {String(slot.dexNo).padStart(3,'0')}</small><strong>{slot.name}</strong>
          {slot.state==='UNDISCOVERED' ? <small>UNDISCOVERED</small> : <><small>{slot.rarity} · {slot.state}</small>
            {slot.state==='DISCOVERED' ? <span>아직 포획하지 않음</span> : <><span>Captured ×{slot.captureCount}</span><time dateTime={slot.firstCapturedAt ?? undefined}>First · {slot.firstCapturedAt?.replace('T',' ').replace('Z',' UTC')}</time></>}
          </>}
        </div>
      </li>)}
    </ol>
  </section>;
}
