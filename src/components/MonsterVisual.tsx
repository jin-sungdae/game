import { resolveMonster } from '../entities/monsters';
import { useBaseAsset } from '../assets/useBaseAsset';
import { rendererSource } from '../assets/base';
import { monsterAnimationUrl, monsterVisualSize, type MonsterAnimationFrame } from '../assets/monster';
import { directionScale } from '../animation/model';
import { BaseSprite, useVisualBounds } from './BaseVisual';
import { PlaceholderRenderer } from './CompanionVisual';
export function MonsterVisual({code,state,facing,animationFrame}:{code:string;state:string;facing:number;animationFrame?:MonsterAnimationFrame}) {
  const definition=resolveMonster(code);
  const base=useBaseAsset(definition?.baseAsset ?? null);
  const animation=useBaseAsset(monsterAnimationUrl(code,definition,animationFrame));
  const {container,bounds}=useVisualBounds();
  const size=monsterVisualSize(code,definition?.visualScale ?? 1,bounds.width,bounds.height);
  const source=rendererSource(animation.url,base.url);
  const name=definition?.name ?? 'Monster';
  return <div ref={container} className={`companion-visual ${source.kind!=='css'?'has-sprite':'has-placeholder'}`}>
    {source.kind==='animation' ? <img className="sprite-frame" src={source.url} alt={name} draggable={false}
      style={{...size,transform:`scaleX(${directionScale(facing)})`}} onError={animation.fail}/>
      : source.kind==='base' ? <BaseSprite character={code.toLowerCase()} state={state} url={source.url} name={name} facing={facing} bounds={size} onError={base.fail}/>
      : <><PlaceholderRenderer facing={facing}/><span className="name">{name}</span><span className="state">{state}</span></>}
  </div>;
}
