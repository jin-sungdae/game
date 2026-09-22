import { monsterDex, rarities } from '../entities/monsterDex';
import { dexEntry, type DexState } from './monsterDex';
import type { CollectionDexPresentation } from '../types/entity';
export const dexFilters = ['ALL', ...rarities] as const;
export type DexFilter = typeof dexFilters[number];
export interface CollectionSlot {
  dexNo: number;
  state: DexState;
  name: string;
  rarity: typeof rarities[number];
  asset: string | null;
  captureCount: number | null;
  firstCapturedAt: string | null;
}
export function collectionDexModel(view?: CollectionDexPresentation, filter: DexFilter = 'ALL') {
  const records = new Map((view?.records ?? []).map(r => [r.monsterCode, r]));
  const progress = { discoveredCodes: new Set(view?.discoveredCodes ?? []), capturedCodes: new Set(records.keys()) };
  // Intentionally include all planning slots; enabled controls spawning, not Dex layout.
  const all: CollectionSlot[] = monsterDex.map(monster => {
    const entry = dexEntry(monster, progress);
    const record = records.get(monster.monsterCode);
    return { dexNo: entry.dexNo, state: entry.state, name: entry.displayName,
      rarity: monster.rarity, asset: entry.state === 'CAPTURED' ? entry.baseAsset : null,
      captureCount: record?.captureCount ?? null, firstCapturedAt: record?.firstCapturedAt ?? null };
  });
  const known = view?.records != null;
  return { slots: all.filter(s => filter === 'ALL' || s.rarity === filter), total: all.length,
    discovered: known ? all.filter(s => s.state !== 'UNDISCOVERED').length : null,
    captured: known ? all.filter(s => s.state === 'CAPTURED').length : null,
    busy: view?.busy ?? false, error: view?.error ?? null,
    message: view?.error ? (known ? '연결 실패 · 마지막 확인 기록입니다. 다시 시도하세요.' : 'Collection을 불러오지 못했습니다. 다시 시도하세요.')
      : view?.busy ? 'Collection 불러오는 중…' : !known ? '새로고침하여 Collection을 확인하세요.'
      : records.size === 0 ? '아직 포획한 Monster가 없습니다.' : '서버 Collection 기록',
  };
}
