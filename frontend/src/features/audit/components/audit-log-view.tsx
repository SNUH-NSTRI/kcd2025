'use client';

import { AuditFiltersBar } from './audit-filters-bar';
import { AuditTimeline } from './audit-timeline';
import { useAuditLogState } from '../context';

export function AuditLogView() {
  const { filteredEvents } = useAuditLogState();

  return (
    <div className="space-y-6">
      <AuditFiltersBar />

      <div className="rounded-lg border border-border/60 bg-card/50 p-4 text-sm text-muted-foreground">
        TrialSynth audit records are append-only. In production, only platform services may write to this log; manual tampering is prohibited and monitored for HIPAA compliance.
      </div>

      <AuditTimeline events={filteredEvents} />
    </div>
  );
}
