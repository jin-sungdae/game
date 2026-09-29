// Native movement owns phase and world geometry; no animation-time integration.
export const jumpPhases=['NEUTRAL','CROUCH','LAUNCH','ASCEND','APEX','DESCEND','LAND','SETTLE'] as const;
export interface JumpSample {phase:string;progress:number;grounded:boolean;vy:number;vx:number;x:number;y:number;timestamp:number;facing:number}
export function jumpFrame(sample:JumpSample|null|undefined,suppressed:boolean,reduced:boolean):number|null {
  if(!sample || suppressed || reduced || ![sample.progress,sample.vy,sample.vx,sample.x,sample.y,sample.timestamp].every(Number.isFinite) || sample.progress<0 || sample.progress>1) return null;
  const i=jumpPhases.indexOf(sample.phase as typeof jumpPhases[number]);
  if(i<2 || i>6 || (sample.phase==='LAND')!==sample.grounded) return null;
  if(sample.phase==='ASCEND' && sample.vy<=0 || sample.phase==='DESCEND' && sample.vy>=0) return null;
  return i;
}
