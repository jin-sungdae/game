import {CandidatePlayback, recipe} from '../../../design/production-batches/luma-asset-16/playback-review/playback.mjs';
// Review-only adapter. Recipes are bound to exact candidate paths, never Species alone.
export function reviewPlayback(directory, count) {
  const match=directory.match(/^\/design\/production-batches\/luma-asset-16\/(M\d{3})\/(sleep|defeat|attack|move)-candidate\/rigged\/\2$/);
  if(!match || count!==12)return null;
  try {return new ReviewPlayback(recipe(match[1],match[2].toUpperCase()));} catch {return null;}
}
export class ReviewPlayback {
  constructor(definition){this.definition=definition;this.restart();}
  restart(){this.player=new CandidatePlayback(this.definition);this.selected=null;}
  wake(){this.player.wake();}
  select(frame){this.selected=frame;}
  resume(){this.selected=null;}
  advance(delta,paused,reduced){if(!paused&&!reduced&&this.selected===null)this.player.advance(Math.min(100,Math.max(0,delta)));return this.sample();}
  sample(){return this.selected===null?this.player.sample():this.selected;}
  get phase(){return this.selected===null?this.player.phase:'selected';}
  get base(){return this.selected===null&&this.player.phase==='done';}
}
