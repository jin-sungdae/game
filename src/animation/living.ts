import type { AnimationInput, AnimationSequence, Pilot } from './pilot';
export interface LivingCue { kind:'OBSERVE'|'REST'|'REACT'|'TURN'; serial:number }
// Only native attention at rest may select an already supplied species-owned clip.
// No gait, jump phase, facing, coordinate, battle or reward decisions live here.
export function livingSequence(p:Pilot,input:AnimationInput,reduced:boolean):AnimationSequence|null {
  const cue=input.livingCue;
  if(!cue || reduced || input.suppressed || input.state!=='ROAMING'
    || !Number.isFinite(input.speed) || input.speed<0 || input.speed>=3
    || !Number.isSafeInteger(cue.serial) || cue.serial<0 || input.jump) return null;
  if(p.character==='MIMI' && (cue.kind==='OBSERVE'||cue.kind==='REACT')) return 'PEEK';
  if(p.character==='PIP' && (cue.kind==='OBSERVE'||cue.kind==='REACT')) return 'REACT';
  if(p.character==='PUFF' && cue.kind==='REST') return 'SETTLE';
  if(p.character==='EMBER' && (cue.kind==='OBSERVE'||cue.kind==='REACT')) return 'INTENSE';
  // Other species keep their own idle/hover/base until an approved clip exists.
  return null;
}
