'use client';

import { AuditLogView } from '@/features/audit/components/audit-log-view';
import { AuditProvider } from '@/features/audit/context';

export default function AuditLogPage() {
  return (
    <AuditProvider>
      <section className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Compliance</p>
          <h1 className="text-3xl font-heading font-semibold text-foreground">Audit log & version history</h1>
          <p className="max-w-2xl text-base text-muted-foreground">
            Inspect append-only timelines for schema edits, cohort generations, analysis runs, and report exports. Filter by entity, collaborator, or timeframe to trace end-to-end provenance across the emulation workflow.
          </p>
        </header>

        <AuditLogView />
      </section>
    </AuditProvider>
  );
}
