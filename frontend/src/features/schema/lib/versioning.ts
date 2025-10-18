import {
  DEFAULT_VERSION_AUTHOR,
  MAX_VERSION_HISTORY,
} from '../constants';
import type { SchemaVersionSnapshot, TrialSchema } from '../types';
import { deepClone, toIsoString } from './utils';
import { describeSchemaChanges } from './change-summary';

interface StoredVersionPayload {
  schema: TrialSchema;
}

function ensureArray(value: unknown): StoredVersionPayload[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => item && typeof item === 'object') as StoredVersionPayload[];
}

export function loadStoredVersions(raw: string | null): SchemaVersionSnapshot[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    const payloads = ensureArray(parsed);
    let previous: TrialSchema | null = null;
    return payloads.map(({ schema }) => {
      const snapshot = {
        schema,
        changes: previous
          ? describeSchemaChanges(previous, schema)
          : ['Initial draft.'],
      } satisfies SchemaVersionSnapshot;
      previous = schema;
      return snapshot;
    });
  } catch (error) {
    console.error('Failed to parse schema versions', error);
    return [];
  }
}

export function saveVersions(
  storageKey: string,
  versions: SchemaVersionSnapshot[],
): void {
  if (typeof window === 'undefined') return;
  const payload = versions
    .slice(-MAX_VERSION_HISTORY)
    .map((snapshot) => ({ schema: snapshot.schema } as StoredVersionPayload));
  window.localStorage.setItem(storageKey, JSON.stringify(payload));
}

export function createSnapshot(
  schema: TrialSchema,
  previous: TrialSchema | null,
): SchemaVersionSnapshot {
  const next = deepClone(schema);
  return {
    schema: next,
    changes: previous ? describeSchemaChanges(previous, next) : ['Initial draft.'],
  };
}

export function withNewVersionMeta(
  schema: TrialSchema,
  message: string,
  author = DEFAULT_VERSION_AUTHOR,
  explicitRev?: number,
): TrialSchema {
  const now = new Date();
  const next = deepClone(schema);
  const nextRev =
    typeof explicitRev === 'number' ? explicitRev : (next.version?.rev ?? 0) + 1;
  next.version = {
    rev: nextRev,
    author,
    timestamp: toIsoString(now),
    message,
  };
  return next;
}
