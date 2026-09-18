import { useEffect, useState } from 'react';
import { BaseAssetLoader } from './base';
const loader=new BaseAssetLoader();
export function useBaseAsset(url:string|null) {
  const [loaded,setLoaded]=useState<string|null>(null);
  useEffect(()=>{
    let disposed=false;
    void loader.load(url).then(value=>{if(!disposed) setLoaded(value);});
    return ()=>{disposed=true;};
  },[url]);
  return {url:loaded===url ? loaded : null,fail:()=>{if(url) loader.fail(url);setLoaded(null);}};
}
