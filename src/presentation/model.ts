import type { Visual } from '../types/entity';
export function hpModel(hp:number,max:number) {
 const ratio=max>0?Math.max(0,Math.min(1,hp/max)):0;
 const tone=ratio>.5?'normal':ratio>=.25?'warning':'critical';
 return {percent:ratio*100,tone,text:`${hp} / ${max}`};
}
// Replace these named effect slots with optional production clips later; no asset timing changes.
export function effectFor(phase:Visual['phase']|undefined,kind:'moa'|'pip') {
 if((kind==='moa'&&phase==='PLAYER_ATTACK')||(kind==='pip'&&phase==='MONSTER_ATTACK'))return 'attack';
 if((kind==='moa'&&phase==='PLAYER_HIT')||(kind==='pip'&&phase==='MONSTER_HIT'))return 'hit';
 if(kind==='pip') {if(phase==='CAPTURING')return 'capturing';if(phase==='CAPTURE_SUCCESS')return 'capture-success';if(phase==='CAPTURE_FAIL')return 'capture-fail';}
 return 'none';
}
export function damageFor(v:Visual|undefined,kind:'moa'|'pip') {
 return v && ((kind==='moa'&&v.phase==='PLAYER_HIT')||(kind==='pip'&&v.phase==='MONSTER_HIT')) ? v.damage : null;
}
