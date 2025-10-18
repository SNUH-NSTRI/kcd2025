import { getSchemaStorageKey } from '@/features/schema/constants';
import { loadStoredVersions } from '@/features/schema/lib/versioning';
import type { TrialSchema } from '@/features/schema/types';

export function loadLatestSchemaByArticles(articleIds: string[]): TrialSchema | null {
  if (typeof window === 'undefined') return null;
  const storageKey = getSchemaStorageKey(articleIds);
  const raw = window.localStorage.getItem(storageKey);
  const versions = loadStoredVersions(raw);
  if (versions.length === 0) return null;
  const latest = versions[versions.length - 1];
  return latest.schema;
}
