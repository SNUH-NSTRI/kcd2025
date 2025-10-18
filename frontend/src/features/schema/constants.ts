export const SCHEMA_STORAGE_PREFIX = 'trial-schema-versions:';
export const DEFAULT_VERSION_AUTHOR = 'TrialSynth Agent';
export const INITIAL_VERSION_MESSAGE = 'Initial auto-extracted draft';
export const MAX_VERSION_HISTORY = 20;

export function getSchemaStorageKey(articleIds: string[]): string {
  const sorted = [...articleIds].sort();
  return `${SCHEMA_STORAGE_PREFIX}${sorted.join('|') || 'unseeded'}`;
}
