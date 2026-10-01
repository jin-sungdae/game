import type { FlightMotion } from './flying';
// A finite native sine-bob excursion, not wing flapping or a timed recovery phase.
export type FloatingState='HOVER'|'FLOAT';
export function resolveFloating(input:{floating?:FlightMotion|null;state:string;suppressed:boolean},previous:FloatingState) {
  const m=input.floating;
  const suppressed=input.suppressed || input.state!=='ROAMING' || !m || ![m.timestamp,m.x,m.y,m.vx,m.vy,m.speed].every(Number.isFinite) || typeof m.active!=='boolean' || m.speed<0 || m.speed>256 || Math.abs(Math.hypot(m.vx,m.vy)-m.speed)>.001;
  // Enter on meaningful movement; remain with the native excursion across a slow apex.
  // Completion/cancellation goes directly to HOVER, without an artificial settle timer.
  const state:FloatingState=!suppressed && m.active && (previous==='FLOAT' || m.speed>=3)?'FLOAT':'HOVER';
  return {state,suppressed:Boolean(suppressed),rate:1};
}
export const floatingClips={HOVER:{name:'hover',frames:4,frameDuration:500},FLOAT:{name:'float',frames:6,frameDuration:200},SETTLE:{name:'settle',frames:2,frameDuration:200}} as const;
export const settleApplicability='NOT_APPLICABLE' as const;
