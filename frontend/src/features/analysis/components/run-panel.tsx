'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { AnalysisRunProgress, AnalysisRunResult } from '@/features/flow/types';

interface RunPanelProps {
  activeRun: AnalysisRunProgress | null;
  onRun: () => void;
  onCancel: () => void;
  canRun: boolean;
  templateName: string | null;
  cohortReady: boolean;
  lastRun: AnalysisRunResult | null;
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div
        className="h-2 rounded-full bg-primary transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export function RunPanel({
  activeRun,
  onRun,
  onCancel,
  canRun,
  templateName,
  cohortReady,
  lastRun,
}: RunPanelProps) {
  const disabledReason = !templateName
    ? 'Select a template to enable analysis.'
    : !cohortReady
      ? 'Generate a cohort before running analyses.'
      : null;

  return (
    <Card className="border border-border/70 bg-card/80">
      <CardHeader className="flex flex-col gap-1">
        <CardTitle className="text-lg">Analysis execution</CardTitle>
        <p className="text-sm text-muted-foreground">
          Run statistical templates on the generated cohort. Results are stored locally for version comparison.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col text-sm text-muted-foreground">
            <span>
              Selected template:{' '}
              <span className="font-medium text-foreground">
                {templateName ?? 'None'}
              </span>
            </span>
            <span>
              Cohort status:{' '}
              <Badge variant={cohortReady ? 'outline' : 'destructive'} className="text-xs">
                {cohortReady ? 'Ready' : 'Not generated'}
              </Badge>
            </span>
          </div>
          <div className="flex gap-2">
            {activeRun ? (
              <Button variant="destructive" onClick={onCancel} size="sm">
                Cancel run
              </Button>
            ) : (
              <Button onClick={onRun} disabled={!canRun} size="sm">
                Start analysis
              </Button>
            )}
          </div>
        </div>

        {disabledReason && !activeRun ? (
          <p className="text-xs text-muted-foreground">{disabledReason}</p>
        ) : null}

        {activeRun ? (
          <div className="space-y-2 rounded-lg border border-border/70 bg-background/60 p-3">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Run ID: {activeRun.runId}</span>
              <span>{activeRun.progress}%</span>
            </div>
            <ProgressBar value={activeRun.progress} />
            <p className="text-xs text-muted-foreground">
              Status: <span className="capitalize">{activeRun.status}</span>
            </p>
          </div>
        ) : null}

        {lastRun ? (
          <div className="rounded-lg border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Previous run</p>
            <p>
              {new Date(lastRun.finishedAt).toLocaleString()} · Duration{' '}
              {(lastRun.durationMs / 1000).toFixed(1)}s
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
