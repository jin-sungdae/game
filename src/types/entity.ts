export type CompanionState = 'IDLE' | 'WALKING' | 'SITTING' | 'LOOKING' | 'SLEEPING' | 'DRAGGING' | 'REACTING';
export type PipState = 'SPAWNING' | 'ROAMING' | 'ENGAGED' | 'DESPAWNING';
export interface Entity { x: number; y: number; state: CompanionState | PipState; facing: number }
export interface Snapshot { moa: Entity; pip: Entity | null; menu: boolean; game?: GamePresentation; visual?: Visual }

export interface Battle { battleId:string;encounterId:string;turn:number;status:string;encounterStatus:string;companion:{hp:number;maxHp:number};monster:{hp:number;maxHp:number};events:string[];reward:{gold:number;exp:number;bond:number}|null }
export interface GamePresentation { encounterId:string|null;monsterLevel:number;battle:Battle|null;busy:boolean;error:string|null;feedback:string|null;collection:{monsterCode:string;captureCount:number}[]; captureChance?:number|null }

export interface Visual {phase:'IDLE'|'REQUESTING'|'PLAYER_ATTACK'|'MONSTER_HIT'|'MONSTER_ATTACK'|'PLAYER_HIT'|'VICTORY'|'CAPTURING'|'CAPTURE_SUCCESS'|'CAPTURE_FAIL'|'REWARD'|'LEVEL_UP'|'ERROR';serial:number;damage:number|null;reward:{gold:number;exp:number;bond:number}|null;level:{from:number;to:number}|null}
