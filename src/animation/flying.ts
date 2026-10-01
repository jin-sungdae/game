// Read-only FLYING presentation; stable speed alone is not a native GLIDE signal.
export interface FlightMotion {timestamp:number;x:number;y:number;vx:number;vy:number;speed:number;active:boolean;facing:number}
export type FlightState='HOVER'|'FLY';
export function resolveFlying(input:{flight?:FlightMotion|null;state:string;suppressed:boolean},previous:FlightState) {
  const m=input.flight;
  const suppressed=input.suppressed || input.state!=='ROAMING' || !m || ![m.timestamp,m.x,m.y,m.vx,m.vy,m.speed].every(Number.isFinite) || m.speed<0 || m.speed>256 || Math.abs(Math.hypot(m.vx,m.vy)-m.speed)>0.001;
  // Match existing motion hysteresis and bounded rate, including vertical movement.
  const state:FlightState=!suppressed && m.speed>=(previous==='FLY'?3:8)?'FLY':'HOVER';
  return {state,suppressed:Boolean(suppressed),rate:state==='FLY'?Math.max(.5,Math.min(2,m!.speed/40)):1};
}
export const flyingClips={HOVER:{name:'hover',frames:4,frameDuration:400},FLY:{name:'fly',frames:6,frameDuration:90},GLIDE:{name:'glide',frames:2,frameDuration:300}} as const;
export const glideApplicability='NOT_APPLICABLE' as const;
