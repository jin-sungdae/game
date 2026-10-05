// Native EDGE follows one vertical safe side; accepted displacement speed is read-only.
export type EdgeState='IDLE'|'EDGE_MOVE';
export function resolveEdge(input:{speed:number;state:string;suppressed:boolean},previous:EdgeState) {
  const suppressed=input.suppressed || input.state!=='ROAMING' || !Number.isFinite(input.speed) || input.speed<0 || input.speed>256;
  const state:EdgeState=!suppressed && input.speed>=(previous==='EDGE_MOVE'?3:8)?'EDGE_MOVE':'IDLE';
  return {state,suppressed,rate:1};
}
export const edgeClips={IDLE:{name:'idle',frames:5,frameDuration:440,loop:true},EDGE_MOVE:{name:'edge_move',frames:6,frameDuration:180,loop:true},TURN:{name:'turn',frames:3,frameDuration:120,loop:false}} as const;
export const turnApplicability='NOT_APPLICABLE' as const;
