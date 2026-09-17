import data from './companions.json';
interface CompanionDefinition {
  name:string; identity:string; palette:string; stages:Record<string,string>;
}
export const companionRegistry:Readonly<Record<string,CompanionDefinition>> = data;
export function resolveCompanion(species:string, evolutionStage:number) {
  if(!Object.hasOwn(companionRegistry,species) || !Number.isSafeInteger(evolutionStage)) return null;
  const definition=companionRegistry[species];
  const assetManifest=definition.stages[String(evolutionStage)];
  if(typeof assetManifest !== 'string') return null;
  return {species,evolutionStage,assetManifest,name:definition.name};
}
