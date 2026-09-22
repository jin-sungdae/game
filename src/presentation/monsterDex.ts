import { monsterDex, type MonsterDefinition } from '../entities/monsterDex';
import { resolveMonster } from '../entities/monsters';
export type DexState = 'UNDISCOVERED' | 'DISCOVERED' | 'CAPTURED';
export interface DexProgress {
  readonly discoveredCodes: ReadonlySet<string>;
  readonly capturedCodes: ReadonlySet<string>;
}
export interface DexEntry {
  readonly dexNo: number;
  readonly monsterCode: string;
  readonly state: DexState;
  readonly displayName: string;
  readonly visual: 'SILHOUETTE' | 'BASE' | 'DIAGNOSTIC';
  readonly baseAsset: string | null;
  readonly visualScale: number;
}
// Pure projection of supplied server evidence; no local discovery/capture persistence.
export function dexEntry(monster: MonsterDefinition, progress: DexProgress): DexEntry {
  const state: DexState = progress.capturedCodes.has(monster.monsterCode) ? 'CAPTURED'
    : progress.discoveredCodes.has(monster.monsterCode) ? 'DISCOVERED' : 'UNDISCOVERED';
  const baseAsset = state === 'UNDISCOVERED' ? null : resolveMonster(monster.monsterCode)?.baseAsset ?? null;
  return Object.freeze({ dexNo: monster.dexNo, monsterCode: monster.monsterCode, state,
    displayName: state === 'UNDISCOVERED' ? '???' : monster.displayName ?? '???',
    visual: state === 'UNDISCOVERED' ? 'SILHOUETTE' : baseAsset ? 'BASE' : 'DIAGNOSTIC',
    baseAsset, visualScale: monster.visualScale });
}
export function dexEntries(progress: DexProgress): readonly DexEntry[] {
  return monsterDex.filter(m => m.enabled).map(m => dexEntry(m, progress));
}
