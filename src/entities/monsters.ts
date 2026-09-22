import data from './monsters.json';
import { resolveMonsterDefinition } from './monsterDex';
export interface MonsterAssetDefinition {
  readonly name: string;
  readonly assetRoot: string;
  readonly baseAsset: string | null;
  readonly animationClips?: Readonly<Partial<Record<'idle' | 'walk' | 'hit' | 'attack' | 'defeat' | 'capture', string>>>;
}
export const monsterRegistry: Readonly<Record<string, MonsterAssetDefinition>> = Object.freeze(
  Object.fromEntries(Object.entries(data).map(([code, asset]) => [code, Object.freeze(asset)])),
);
// Future clips live below assetRoot; a design slot never implies a production PNG exists.
export function resolveMonster(code: string): MonsterAssetDefinition | null {
  if (Object.hasOwn(monsterRegistry, code)) return monsterRegistry[code];
  const content = resolveMonsterDefinition(code);
  return content ? Object.freeze({
    name: content.displayName ?? 'Monster',
    assetRoot: `/assets/monsters/${content.assetIdentity}`,
    baseAsset: null,
  }) : null;
}
