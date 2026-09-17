export type CompanionState = 'IDLE' | 'WALKING' | 'SITTING' | 'LOOKING' | 'SLEEPING' | 'DRAGGING' | 'REACTING';
export type PipState = 'SPAWNING' | 'ROAMING' | 'ENGAGED' | 'DESPAWNING';
export interface Entity { x: number; y: number; state: CompanionState | PipState; facing: number }
export interface Snapshot { moa: Entity; pip: Entity | null; menu: boolean }
