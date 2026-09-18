import { resolveMonster } from '../entities/monsters';
import { useBaseAsset } from '../assets/useBaseAsset';
import { BaseSprite, useVisualBounds } from './BaseVisual';
import { PlaceholderRenderer } from './CompanionVisual';
export function MonsterVisual({code,state,facing}:{code:string;state:string;facing:number}) {
  const definition=resolveMonster(code);
  const base=useBaseAsset(definition?.baseAsset ?? null);
  const {container,bounds}=useVisualBounds();
  const name=definition?.name ?? 'Monster';
  return <div ref={container} className={`companion-visual ${base.url?'has-sprite':'has-placeholder'}`}>
    {base.url ? <BaseSprite character={code.toLowerCase()} state={state} url={base.url} name={name} facing={facing} bounds={bounds} onError={base.fail}/>
      : <><PlaceholderRenderer facing={facing}/><span className="name">{name}</span><span className="state">{state}</span></>}
  </div>;
}
