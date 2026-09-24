export type CompanionState = 'IDLE' | 'WALKING' | 'SITTING' | 'LOOKING' | 'SLEEPING' | 'DRAGGING' | 'REACTING';
export type PipState = 'SPAWNING' | 'ROAMING' | 'ENGAGED' | 'DESPAWNING';
export interface Entity { x: number; y: number; state: CompanionState | PipState; facing: number }
export interface MonsterIdentity {monsterCode:string;assetIdentity:string;rarity:string;level:number;encounterId:string|null;movementProfile:string}
export interface Snapshot { animation?:{moa:number;pip:number}; bond?:{busy:boolean;feedback:string|null;nextAvailableAt:string|null}; monster?:MonsterIdentity|null; moa: Entity; pip: Entity | null; menu: boolean; game?: GamePresentation; visual?: Visual; identity?: CompanionIdentity|null; evolution?: EvolutionPresentation; items?: ItemPresentation; dex?:CollectionDexPresentation; interaction?:'DEX'|'ENCOUNTER'|'EVOLUTION'|'SHOP'|'INVENTORY'|'BATTLE_ITEMS' }

export interface Battle { battleId:string;encounterId:string;turn:number;status:string;encounterStatus:string;companion:{hp:number;maxHp:number};monster:{hp:number;maxHp:number};events:string[];reward:{gold:number;exp:number;bond:number}|null }
export interface GamePresentation { encounterId:string|null;monsterLevel:number;battle:Battle|null;busy:boolean;error:string|null;feedback:string|null;collection:{monsterCode:string;captureCount:number}[]; captureChance?:number|null;captureBaseChance?:number|null;captureItemBonus?:number|null;captureFinalChance?:number|null }

export interface Visual {phase:'IDLE'|'REQUESTING'|'PLAYER_ATTACK'|'MONSTER_HIT'|'MONSTER_ATTACK'|'PLAYER_HIT'|'VICTORY'|'CAPTURING'|'CAPTURE_SUCCESS'|'CAPTURE_FAIL'|'REWARD'|'LEVEL_UP'|'ERROR';serial:number;damage:number|null;reward:{gold:number;exp:number;bond:number}|null;level:{from:number;to:number}|null}

export interface CompanionIdentity {playerCompanionId:number;species:string;evolutionStage:number;evolutionName:string;level:number;exp:number;bond:number}
export interface EvolutionEligibility {status:'LOCKED'|'AVAILABLE'|'MAX_STAGE';species:string;currentStage:number;currentName:string;nextStage:number|null;nextName:string|null;requirements:{level:{required:number;current:number;met:boolean};bond:{required:number;current:number;met:boolean}}|null}
export interface EvolutionPresentation {eligibility:EvolutionEligibility|null;busy:boolean;error:string|null;phase:'IDLE'|'GLOW'|'REVEAL';previous:CompanionIdentity|null;success:string|null}

export interface ShopItem {itemCode:string;itemName:string;itemType:string;price:number;ownedQuantity:number;maxStack:number}
export interface OwnedItem {itemCode:string;itemName:string;itemType:string;quantity:number}
export interface ItemEffect {battleId:string;effectType:string;value:number;armed:boolean;consumedAt:string|null}
export interface ItemPresentation {inventory:{gold:number;shop:ShopItem[];owned:OwnedItem[];effects:ItemEffect[]}|null;busy:boolean;error:string|null;feedback:string|null}

export interface CollectionRecord {monsterCode:string;monsterName:string;captureCount:number;firstCapturedAt:string;lastCapturedAt:string}
export interface CollectionDexPresentation {records:CollectionRecord[]|null;discoveredCodes:string[];busy:boolean;error:string|null}
