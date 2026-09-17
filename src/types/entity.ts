export type MoaState = 'IDLE' | 'WALKING' | 'DRAGGING' | 'REACTING';
export type PipState = 'SPAWNING' | 'ROAMING' | 'ENGAGED' | 'DESPAWNING';
export interface Entity { x: number; y: number; state: MoaState | PipState; facing: number }
export interface Snapshot { moa: Entity; pip: Entity | null; menu: boolean }
