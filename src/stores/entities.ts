import { useSyncExternalStore } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import type { Snapshot } from '../types/entity';
let snapshot: Snapshot = { moa: { x:0,y:0,state:'IDLE',facing:-1 }, pip:null, menu:false };
const listeners = new Set<() => void>();
function update(value: Snapshot) { snapshot = value; listeners.forEach(fn => fn()); }
export async function connect() {
  const unlisten = await listen<Snapshot>('world', event => update(event.payload));
  update(await invoke<Snapshot>('snapshot'));
  return unlisten;
}
export const useEntities = () => useSyncExternalStore(callback => { listeners.add(callback); return () => { listeners.delete(callback); }; }, () => snapshot);
