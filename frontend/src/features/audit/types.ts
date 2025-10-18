export type AuditEntity = 'schema' | 'cohort' | 'analysis' | 'report' | 'flow';

export interface AuditEvent {
  id: string;
  ts: number;
  actor: string;
  entity: AuditEntity;
  action: string;
  metadata: Record<string, unknown>;
}

export type AuditRange = '7d' | '30d' | '90d' | 'all';

export interface AuditFilters {
  entity: AuditEntity | 'all';
  actor: string | 'all';
  range: AuditRange;
}
