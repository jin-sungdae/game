import {CandidatePlayback, recipe} from '../../../design/production-batches/luma-asset-16/playback-review/playback.mjs';
const followupRoot = '/design/production-batches/action-followup/';
const sourceRoot = '/design/production-batches/monsters/';
const followupCandidates = new Map([
  ['M088/interact-pilot/rigged/interact', sourceRoot + 'batch09/M088/base-v2.png'],
  ['M090/hit-pilot/rigged/hit', sourceRoot + 'batch09/M090/base-v2.png'],
  ['M092/hit-pilot/rigged/hit', sourceRoot + 'batch10/M092/base-v2.png'],
  ['M096/cursor_react-pilot/rigged/cursor_react', sourceRoot + 'batch10/M096/base-v2.png'],
]);

// Review-only adapter. Recipes are bound to exact candidate paths, never Species alone.
export function reviewPlayback(directory, count, frameDuration = 0) {
  if (directory === '/design/production-batches/luma-asset-20/M085/breath/rigged/breath') {
    if (count !== 8 || !Number.isFinite(frameDuration) || frameDuration <= 0) return null;
    const frames = Array.from({ length: count }, (_, frame) => ({ frame, ms: frameDuration }));
    return new ReviewPlayback({
      initial: 'breath',
      phases: { breath: { frames, next: 'breath' } },
    }, sourceRoot + 'batch09/M085/base-v2.png');
  }
  const basePath = directory.startsWith(followupRoot) ? followupCandidates.get(directory.slice(followupRoot.length)) : undefined;
  if (basePath) {
    if (count !== 8 || !Number.isFinite(frameDuration) || frameDuration <= 0) return null;
    const frames = Array.from({length: count}, (_, frame) => ({frame, ms: frameDuration}));
    return new ReviewPlayback({
      initial: 'one-shot',
      phases: {
        'one-shot': {frames, next: 'done'},
        done: {frames: [frames[count - 1]], next: 'done'},
      },
    }, basePath);
  }
  const match=directory.match(/^\/design\/production-batches\/luma-asset-16\/(M\d{3})\/(sleep|defeat|attack|move)-candidate\/rigged\/\2$/);
  if(!match || count!==12)return null;
  try {return new ReviewPlayback(recipe(match[1],match[2].toUpperCase()));} catch {return null;}
}
export class ReviewPlayback {
  constructor(definition,basePath=null){this.definition=definition;this.basePath=basePath;this.restart();}
  restart(){this.player=new CandidatePlayback(this.definition);this.selected=null;}
  wake(){this.player.wake();}
  select(frame){this.selected=frame;}
  resume(){this.selected=null;}
  advance(delta,paused,reduced){if(!paused&&!reduced&&this.selected===null)this.player.advance(Math.min(100,Math.max(0,delta)));return this.sample();}
  sample(){return this.selected===null?this.player.sample():this.selected;}
  get phase(){return this.selected===null?this.player.phase:'selected';}
  get base(){return this.selected===null&&this.player.phase==='done';}
}
