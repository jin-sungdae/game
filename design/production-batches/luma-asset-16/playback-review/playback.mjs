// Offline candidate timing only. No Runtime or approval state is changed.
const frames = (indices, durations) => indices.map((frame, i) => ({frame, ms: Array.isArray(durations) ? durations[i] : durations}));
const all = Array.from({length: 12}, (_, i) => i);
export function recipe(monster, action) {
  if (monster === 'M061' && action === 'SLEEP') return {
    initial: 'enter', phases: {
      enter: {frames: frames([0,1,2,3,4], [240,300,360,420,500]), next: 'hold'},
      hold: {frames: frames([5,6,7,8,7,6], 600), next: 'hold', wake: 'exit'},
      exit: {frames: frames([9,10,11], [450,350,300]), next: 'done'},
      done: {frames: frames([11], 1000), next: 'done'}
    }
  };
  if (['M061','M062','M064'].includes(monster) && action === 'DEFEAT') return {
    initial: 'fall', phases: {
      fall: {frames: frames(all, [100,100,120,140,160,180,200,230,260,300,350,450]), next: 'held'},
      held: {frames: frames([11], 1000), next: 'held'}
    }
  };
  if (['M061','M062'].includes(monster) && action === 'ATTACK') return {
    initial: 'attack', phases: {
      attack: {frames: frames(all, [140,140,160,180,80,55,65,90,140,170,200,240]), next: 'done'},
      done: {frames: frames([11], 1000), next: 'done'}
    }
  };
  if (monster === 'M061' && action === 'MOVE') return {
    initial: 'stroke', phases: {
      stroke: {frames: frames(all, [120,90,70,70,85,100,120,140,150,140,120,120]), next: 'stroke'}
    }
  };
  throw new Error('No approved-for-review timing recipe for this candidate');
}
export class CandidatePlayback {
  constructor(definition) {
    this.definition = definition;
    this.phase = definition.initial;
    this.index = 0;
    this.elapsed = 0;
    this.wakeRequested = false;
  }
  wake() { this.wakeRequested = true; }
  sample() { return this.definition.phases[this.phase].frames[this.index].frame; }
  advance(ms) {
    if (!Number.isFinite(ms) || ms < 0) throw new Error('Invalid elapsed time');
    this.elapsed += ms;
    while (this.elapsed >= this.definition.phases[this.phase].frames[this.index].ms) {
      const phase = this.definition.phases[this.phase];
      this.elapsed -= phase.frames[this.index].ms;
      if (++this.index === phase.frames.length) {
        this.phase = this.wakeRequested && phase.wake ? phase.wake : phase.next;
        this.index = 0;
      }
      // A terminal hold consumes time without repeated state changes.
      const next = this.definition.phases[this.phase];
      if (next.frames.length === 1 && next.next === this.phase && !next.wake) {
        this.elapsed %= next.frames[0].ms;
        break;
      }
    }
    return this.sample();
  }
}
