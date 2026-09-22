import durations from './spawnDurations.json';
// Rarity is the validated server/content identity; never inferred from species or time.
export function spawnPresentation(rarity:string|undefined,state:string,interrupted:boolean) {
  if(state!=='SPAWNING' || interrupted || !rarity || !['UNCOMMON','RARE','SPECIAL'].includes(rarity)) return null;
  const tier=rarity as 'UNCOMMON'|'RARE'|'SPECIAL';
  return {tier:tier.toLowerCase(),duration:durations[tier]};
}
