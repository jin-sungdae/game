// Presentation only: no state transitions, timing decisions or world coordinates.
export type BaseMotion = 'idle'|'walk'|'look'|'sit'|'sleep'|'react'|'still';
const moa:Readonly<Record<string,BaseMotion>> = {
  IDLE:'idle', WALKING:'walk', LOOKING:'look', SITTING:'sit',
  SLEEPING:'sleep', REACTING:'react', DRAGGING:'still',
};
const pip:Readonly<Record<string,BaseMotion>> = {
  SPAWNING:'idle', ROAMING:'walk', ENGAGED:'idle', DESPAWNING:'still',
};
export function baseMotion(character:string,state:string) {
  const states=character==='moa' ? moa : character==='pip' ? pip : null;
  const motion=states && Object.hasOwn(states,state) ? states[state] : 'still';
  return {className:`base-motion bm-${character==='pip'?'pip':'moa'}-${motion}`,sleep:character==='moa' && motion==='sleep'};
}
