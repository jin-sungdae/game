// One clock per WebView, shared by all subscribers; none survives the last entity.
export class AnimationClock {
  private listeners=new Set<(time:number)=>void>();private request:number|null=null;
  constructor(private raf:(cb:FrameRequestCallback)=>number,private cancel:(id:number)=>void) {}
  subscribe(fn:(time:number)=>void) {
    this.listeners.add(fn);
    if(this.request===null) this.request=this.raf(this.tick);
    return ()=>{this.listeners.delete(fn);if(!this.listeners.size && this.request!==null){this.cancel(this.request);this.request=null;}};
  }
  private tick=(time:number)=>{this.request=null;for(const fn of this.listeners)fn(time);if(this.listeners.size)this.request=this.raf(this.tick);};
}
export const animationClock=new AnimationClock(cb=>requestAnimationFrame(cb),id=>cancelAnimationFrame(id));
