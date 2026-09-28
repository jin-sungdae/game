import type { IdleSequences } from './model';
// One entropy read per renderer lifetime; injectable, reproducible PRNG for tests.
export function seededRandom(seed:number):()=>number {
  let state=seed>>>0;
  return ()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296;};
}
export function idleRandom():()=>number {
  return seededRandom(crypto.getRandomValues(new Uint32Array(1))[0]);
}
// Pure shared-clock consumer. No timer, RAF, network, or world-state ownership.
export class IdleSequencer {
  private next:number|null=null;
  private blinking:number|null=null;
  constructor(private readonly random:()=>number) {}
  reset() {this.next=null;this.blinking=null;}
  sample(time:number,active:boolean,reduced:boolean,config:IdleSequences|undefined,blinkDuration:number) {
    if(!active || reduced || !config) {this.reset();return 'IDLE' as const;}
    const schedule=()=>{
      const value=this.random();
      const unit=Number.isFinite(value)?Math.max(0,Math.min(1,value)):0;
      this.next=time+config.blinkIntervalMs[0]+unit*(config.blinkIntervalMs[1]-config.blinkIntervalMs[0]);
    };
    if(this.blinking!==null) {
      if(time-this.blinking<blinkDuration) return 'BLINK' as const;
      this.blinking=null;schedule();return 'IDLE' as const;
    }
    if(this.next===null) schedule();
    if(time>=this.next!) {this.blinking=time;this.next=null;return 'BLINK' as const;}
    return 'IDLE' as const;
  }
}
