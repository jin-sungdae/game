import type { Clip } from './model';
export class AnimationController {
  private identity = '';
  private started = 0;
  private clip:Clip = {frames:1,frameDuration:100,loop:false};
  constructor(private readonly now:()=>number = () => performance.now()) {}
  select(identity:string, clip:Clip) {
    if(identity === this.identity) return;
    this.identity = identity;
    this.clip = clip;
    this.started = this.now();
  }
  sample() {
    const elapsed = Math.max(0, this.now()-this.started);
    const index = Math.floor(elapsed/this.clip.frameDuration);
    return {frame:this.clip.loop ? index%this.clip.frames : Math.min(index,this.clip.frames-1),
      elapsed, finished:!this.clip.loop && index >= this.clip.frames};
  }
}
