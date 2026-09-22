import type { OwnedItem, ItemPresentation } from '../types/entity';
// UI lists contexts, never simulates HP/bond/chance or computes authoritative eligibility.
export function usableItems(items:OwnedItem[],battle:boolean) {
 return items.filter(i=>battle?['SMALL_POTION','CAPTURE_CHARM'].includes(i.itemCode):i.itemCode==='BOND_BERRY');
}
export function itemView(view?:ItemPresentation,otherBusy=false) {
 return {busy:Boolean(view?.busy||otherBusy),gold:view?.inventory?.gold??null,
  message:view?.busy?'Connecting…':view?.error?`${view.error}. Refresh before another command.`:view?.feedback??'',
  shop:view?.inventory?.shop??[],owned:view?.inventory?.owned??[],effects:view?.inventory?.effects??[]};
}
