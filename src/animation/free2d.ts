// Accepted native 2D displacement magnitude, not horizontal-only speed or world authority.
export type Free2dState='FLICKER'|'FLOW';
export function resolveFree2d(input:{speed:number;state:string;suppressed:boolean},previous:Free2dState) {
  const suppressed=input.suppressed || input.state!=='ROAMING' || !Number.isFinite(input.speed) || input.speed<0 || input.speed>256;
  const state:Free2dState=!suppressed && (previous==='FLOW'?input.speed>3:input.speed>=8)?'FLOW':'FLICKER';
  return {state,suppressed,rate:1};
}
export const free2dClips={FLICKER:{name:'flicker',frames:5,frameDuration:360,loop:true},FLOW:{name:'flow',frames:6,frameDuration:160,loop:true},INTENSE:{name:'intense',frames:4,frameDuration:120,loop:true}} as const;
export const intenseApplicability='NOT_APPLICABLE' as const;
