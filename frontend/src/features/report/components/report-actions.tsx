'use client';

import { Button } from '@/components/ui/button';

interface ReportActionsProps {
  onGenerate: () => void;
  onDownloadJson: () => void;
  onPrint: () => void;
  hasReport: boolean;
  lastGeneratedAt: string | null;
}

export function ReportActions({
  onGenerate,
  onDownloadJson,
  onPrint,
  hasReport,
  lastGeneratedAt,
}: ReportActionsProps) {
  const formatted = lastGeneratedAt ? new Date(lastGeneratedAt).toLocaleString() : null;

  return (
    <div className="no-print flex flex-wrap items-center gap-3 rounded-lg border border-border/70 bg-card/60 p-4">
      <div className="flex flex-col gap-1 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Report orchestration</span>
        {formatted ? <span>Last generated {formatted}</span> : <span>Generate to view the latest draft narrative.</span>}
      </div>
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={onGenerate}>
          {hasReport ? 'Regenerate draft' : 'Generate draft'}
        </Button>
        <Button variant="ghost" onClick={onDownloadJson} disabled={!hasReport}>
          Download JSON
        </Button>
        <Button onClick={onPrint} disabled={!hasReport}>
          Print / Save PDF
        </Button>
      </div>
    </div>
  );
}
