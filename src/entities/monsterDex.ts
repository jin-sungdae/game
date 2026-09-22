import data from './monster-dex.json';

export const rarities = ['COMMON', 'UNCOMMON', 'RARE', 'EPIC', 'SPECIAL'] as const;
export const archetypes = ['BEAST', 'SLIME', 'PLANT', 'SPIRIT', 'BIRD', 'INSECT', 'AQUATIC', 'ROCK', 'SHADOW', 'MECHANICAL', 'MIMIC', 'COSMIC'] as const;
// Wire values of src-tauri/src/movement/mod.rs::MovementProfile; no new engine.
export const movementProfiles = ['GROUND', 'JUMP', 'FREE_2D', 'FLOATING', 'FLYING', 'EDGE', 'STATIC'] as const;
export const behaviorProfiles = ['CURIOUS', 'TIMID', 'PLAYFUL', 'AGGRESSIVE', 'SLEEPY', 'TRICKSTER', 'PASSIVE'] as const;
export const spawnProfiles = ['BOTTOM', 'TOP', 'EDGE', 'FREE_AREA', 'NEAR_DOCK', 'NEAR_DESKTOP_EDGE', 'FLOATING_AREA'] as const;
export const spawnConditions = ['ANY_TIME', 'DAY', 'NIGHT', 'FOCUS_SESSION', 'SPECIAL_EVENT'] as const;
function choice<T extends string>(values: readonly T[], value: unknown): T {
  if (typeof value !== 'string' || !values.includes(value as T)) throw new Error(`Unknown content value: ${String(value)}`);
  return value as T;
}
export const parseRarity = (v: unknown) => choice(rarities, v);
export const parseArchetype = (v: unknown) => choice(archetypes, v);
export const parseMovementProfile = (v: unknown) => choice(movementProfiles, v);
export const parseBehaviorProfile = (v: unknown) => choice(behaviorProfiles, v);
export const parseSpawnProfile = (v: unknown) => choice(spawnProfiles, v);
export const parseSpawnCondition = (v: unknown) => choice(spawnConditions, v);
export interface MonsterDefinition {
  readonly dexNo: number;
  readonly monsterCode: string;
  readonly displayName: string | null;
  readonly workingName: string;
  readonly rarity: ReturnType<typeof parseRarity>;
  readonly archetype: ReturnType<typeof parseArchetype>;
  readonly movementProfile: ReturnType<typeof parseMovementProfile>;
  readonly behaviorProfile: ReturnType<typeof parseBehaviorProfile>;
  readonly spawnProfile: ReturnType<typeof parseSpawnProfile>;
  readonly spawnCondition: ReturnType<typeof parseSpawnCondition>;
  // Design/reference values only. Server m_monster and CombatRules remain authoritative.
  readonly encounterWeight: number;
  readonly baseCaptureRate: number | null;
  readonly visualScale: number;
  readonly assetIdentity: string;
  readonly enabled: boolean;
  readonly alphaCandidate: boolean;
  readonly captureDirection: string;
  readonly visualTheme: string;
  readonly productionStatus: 'PRODUCTION' | 'PROVISIONAL';
}
function text(v: unknown): string {
  if (typeof v !== 'string' || !v.trim()) throw new Error('Expected nonempty content text');
  return v;
}
function number(v: unknown, min: number, max: number, integer = false): number {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < min || v > max || (integer && !Number.isSafeInteger(v))) throw new Error('Content number out of bounds');
  return v;
}
function boolean(v: unknown): boolean {
  if (typeof v !== 'boolean') throw new Error('Expected content boolean');
  return v;
}
export function parseMonsterDefinitions(input: unknown): readonly MonsterDefinition[] {
  if (!Array.isArray(input)) throw new Error('Expected content array');
  const codes = new Set<string>();
  const numbers = new Set<number>();
  return Object.freeze(input.map((value: unknown): MonsterDefinition => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected content object');
    const v = value as Record<string, unknown>;
    const monsterCode = text(v.monsterCode);
    const assetIdentity = text(v.assetIdentity);
    if (!/^[A-Z][A-Z0-9_]*$/.test(monsterCode) || !/^[a-z][a-z0-9_]*$/.test(assetIdentity)) throw new Error('Invalid identity');
    const dexNo = number(v.dexNo, 1, Number.MAX_SAFE_INTEGER, true);
    if (codes.has(monsterCode) || numbers.has(dexNo)) throw new Error('Duplicate Monster code or Dex number');
    codes.add(monsterCode); numbers.add(dexNo);
    const result: MonsterDefinition = {
      dexNo, monsterCode, assetIdentity,
      displayName: v.displayName === null ? null : text(v.displayName), workingName: text(v.workingName),
      rarity: parseRarity(v.rarity), archetype: parseArchetype(v.archetype),
      movementProfile: parseMovementProfile(v.movementProfile), behaviorProfile: parseBehaviorProfile(v.behaviorProfile),
      spawnProfile: parseSpawnProfile(v.spawnProfile), spawnCondition: parseSpawnCondition(v.spawnCondition),
      encounterWeight: number(v.encounterWeight, 0, Number.MAX_SAFE_INTEGER, true),
      baseCaptureRate: v.baseCaptureRate === null ? null : number(v.baseCaptureRate, 0, 1),
      visualScale: number(v.visualScale, 0.5, 1.5), enabled: boolean(v.enabled), alphaCandidate: boolean(v.alphaCandidate),
      captureDirection: text(v.captureDirection), visualTheme: text(v.visualTheme),
      productionStatus: choice(['PRODUCTION', 'PROVISIONAL'] as const, v.productionStatus),
    };
    if (result.enabled && (result.productionStatus !== 'PRODUCTION' || result.displayName === null || result.encounterWeight === 0 || result.baseCaptureRate === null)) throw new Error('Enabled Monster requires confirmed production metadata');
    return Object.freeze(result);
  }));
}
export const monsterDex = parseMonsterDefinitions(data);
export function resolveMonsterDefinition(code: string): MonsterDefinition | null {
  return monsterDex.find(m => m.monsterCode === code) ?? null;
}
// Catalog visibility only: never use this as the server encounter candidate set.
export function enabledMonsterDefinitions(): readonly MonsterDefinition[] {
  return monsterDex.filter(m => m.enabled);
}
