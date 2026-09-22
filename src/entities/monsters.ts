import data from './monsters.json';
import { resolveMonsterDefinition } from './monsterDex';
export interface MonsterAssetDefinition {
  readonly name: string;
  readonly assetRoot: string;
  readonly baseAsset: string | null;
  readonly visualScale: number;
  readonly alphaDelivery: boolean;
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
    visualScale: content.visualScale,
    alphaDelivery: false,
  }) : null;
}

// Delivery contract only; neither this registry nor asset existence enables gameplay.
export const monsterAssetContract = Object.freeze({
  width:256, height:256, format:'PNG', color:'RGBA', transparent:true,
  anchor:'bottom-center', sourceFacing:'RIGHT', minimumScale:.5, maximumScale:1.5,
} as const);
export function validMonsterScale(value:unknown):value is number {
  return typeof value==='number' && Number.isFinite(value) && value>=.5 && value<=1.5;
}
