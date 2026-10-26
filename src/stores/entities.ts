import { useSyncExternalStore } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import { SkillTimeline } from '../presentation/skill';
import type { Snapshot } from '../types/entity';
let snapshot: Snapshot = { moa: { x:0,y:0,state:'IDLE',facing:-1 }, pip:null, menu:false };
const listeners = new Set<() => void>();
// Observe server cues when snapshots arrive, including while the battle panel is unmounted.
export const skillTimeline = new SkillTimeline();
function update(value: Snapshot) {
 const battle=value.game?.battle;
 if(battle){skillTimeline.selectBattle(battle.battleId);if(battle.skillCue)skillTimeline.observe(battle.skillCue,performance.now());}
 snapshot = value; listeners.forEach(fn => fn());
}
export async function connect() {
  let receivedWorld=false;
  const unlisten = await listen<Snapshot>('world', event => {receivedWorld=true;update(event.payload);});
  try {
    const initial=await invoke<Snapshot>('snapshot');
    // The initial response may arrive after a newer native event. Never rewind its state/cue.
    if(!receivedWorld)update(initial);
    return unlisten;
  } catch(error) {
    unlisten();
    throw error;
  }
}
export const useEntities = () => useSyncExternalStore(callback => { listeners.add(callback); return () => { listeners.delete(callback); }; }, () => snapshot);
