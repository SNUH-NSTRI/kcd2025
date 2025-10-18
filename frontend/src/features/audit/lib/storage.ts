import { AUDIT_STORAGE_KEY } from '../constants';
import type { AuditEvent } from '../types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeEvent(input: unknown): AuditEvent | null {
  if (!isRecord(input)) return null;
  const { id, ts, actor, entity, action, metadata } = input;
  if (typeof id !== 'string' || typeof actor !== 'string' || typeof entity !== 'string') {
    return null;
  }
  if (typeof action !== 'string') return null;
  if (typeof ts !== 'number' || Number.isNaN(ts)) return null;
  const safeMetadata = isRecord(metadata) ? metadata : {};
  return {
    id,
    ts,
    actor,
    entity: entity as AuditEvent['entity'],
    action,
    metadata: safeMetadata,
  };
}

export function loadStoredEvents(raw: string | null): AuditEvent[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const events = parsed
      .map((item) => normalizeEvent(item))
      .filter((item): item is AuditEvent => item !== null)
      .sort((a, b) => b.ts - a.ts);
    return events;
  } catch (error) {
    console.error('Failed to parse audit log storage', error);
    return [];
  }
}

export function persistEvents(events: AuditEvent[]) {
  if (typeof window === 'undefined') return;
  try {
    const payload = JSON.stringify(events);
    window.localStorage.setItem(AUDIT_STORAGE_KEY, payload);
  } catch (error) {
    console.error('Failed to persist audit log', error);
  }
}

export function clearEvents() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(AUDIT_STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear audit log storage', error);
  }
}
