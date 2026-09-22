import { action } from '../overlay/bridge';
import { itemView,usableItems } from '../presentation/items';
import type { ItemPresentation } from '../types/entity';
export function ItemInteraction({view,mode,otherBusy,battleActive}:{view?:ItemPresentation;mode:'SHOP'|'INVENTORY'|'BATTLE_ITEMS';otherBusy:boolean;battleActive:boolean}) {
 const m=itemView(view,otherBusy);const battle=mode==='BATTLE_ITEMS'||battleActive;
 return <section className="interaction gp-panel" aria-label={mode==='SHOP'?'Shop':'Inventory'}>
  <header className="gp-header"><div><small>{battle?'BATTLE ITEMS':'COMPANION'}</small><strong>{mode==='SHOP'?'Shop':'Inventory'}</strong></div><button aria-label="Close panel" onClick={()=>void action('close')}>×</button></header>
  <small>Gold {m.gold??'—'} G</small>
  <div className="gp-actions"><button disabled={m.busy} onClick={()=>void action('shop')}>Shop</button><button disabled={m.busy} onClick={()=>void action(battle?'battle-items':'inventory')}>Inventory</button><button disabled={m.busy} onClick={()=>void action('items-refresh')}>Refresh</button><button onClick={()=>void action(battle?'interact':'evolution')}>Back</button></div>
  {mode==='SHOP'?m.shop.map(i=><div className="item-row" key={i.itemCode}><span>{i.itemName}<small>{i.price} G · Owned {i.ownedQuantity}/{i.maxStack}</small></span><button disabled={m.busy||!view?.inventory} onClick={()=>void action(`buy:${i.itemCode}`)}>BUY</button></div>):usableItems(m.owned,battle).map(i=><div className="item-row" key={i.itemCode}><span>{i.itemName}<small>Owned {i.quantity}</small></span><button disabled={m.busy||i.quantity===0} onClick={()=>void action(`use:${i.itemCode}`)}>USE</button></div>)}
  {mode!=='SHOP'&&usableItems(m.owned,battle).length===0&&<small>No items. Visit Shop.</small>}
  {battle&&m.effects.filter(e=>e.armed).map(e=><small key={e.effectType}>Charm Ready · +{Math.round(e.value*100)}%</small>)}
  <p role={view?.error?'alert':'status'} className="gp-status">{m.message}</p>
 </section>;
}
