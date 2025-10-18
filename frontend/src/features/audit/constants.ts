import type { AuditFilters } from './types';

export const AUDIT_STORAGE_KEY = '3vto:audit-log';
export const DEFAULT_ACTOR = 'Emily Lee';

export const DEFAULT_FILTERS: AuditFilters = {
  entity: 'all',
  actor: 'all',
  range: '30d',
};

export const RANGE_TO_MS: Record<Exclude<AuditFilters['range'], 'all'>, number> = {
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
  '90d': 90 * 24 * 60 * 60 * 1000,
};

export const ENTITY_LABELS: Record<string, string> = {
  schema: 'Schema',
  cohort: 'Cohort',
  analysis: 'Analysis',
  report: 'Report',
  flow: 'Flow',
};
