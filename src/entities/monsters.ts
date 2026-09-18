import data from './monsters.json';
interface MonsterAssetDefinition { name:string; assetRoot:string; baseAsset:string }
export const monsterRegistry:Readonly<Record<string,MonsterAssetDefinition>>=data;
// Future clips may live below assetRoot/{idle,walk,hit,attack,defeat,capture}.
export function resolveMonster(code:string):MonsterAssetDefinition|null {
  return Object.hasOwn(monsterRegistry,code) ? monsterRegistry[code] : null;
}
