import type { CompanionIdentity, EvolutionPresentation } from '../types/entity';
// Eligibility is an enum supplied by the server, never recomputed from progression.
export function evolutionModel(view?:EvolutionPresentation, gameBusy=false) {
  const status=view?.eligibility?.status;
  return {available:status==='AVAILABLE',canEvolve:status==='AVAILABLE' && !view?.busy && !gameBusy && view?.phase==='IDLE',
    title:view?.eligibility?.nextName ? `${view.eligibility.nextName}로 진화` : view?.eligibility?.currentName ?? 'Evolution',
    message:view?.busy?'서버 확인 중…':view?.error ?? (view?.success?`${view.success} 진화 완료`:status==='MAX_STAGE'?'최종 진화 단계':status==='LOCKED'?'현재 진화할 수 없습니다.':status==='AVAILABLE'?'진화할 준비가 되었습니다.':'서버 연결을 기다립니다.')};
}
export function renderIdentity(identity?:CompanionIdentity|null, view?:EvolutionPresentation) {
  return view?.phase==='GLOW' && view.previous ? view.previous : identity;
}
