// STATIC presentation never derives movement or secondary events from speed.
export function resolveStatic(input:{state:string;suppressed:boolean}) {
  return {state:'IDLE' as const,suppressed:input.suppressed || input.state!=='ROAMING',rate:1};
}
export const staticClips={IDLE:{name:'idle',frames:5,frameDuration:500,loop:true},PEEK:{name:'peek',frames:5,frameDuration:120,loop:false}} as const;
// MIMI attention is supplied by the native species controller through livingSequence.
export const peekApplicability='NATIVE_ATTENTION' as const;
