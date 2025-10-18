'use client';

import { useMemo } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import type { AnalysisRunResult } from '@/features/flow/types';

interface CompareDrawerProps {
  runs: AnalysisRunResult[];
  selection: string[];
  onSelectionChange: (runIds: string[]) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CompareDrawer({ runs, selection, onSelectionChange, open, onOpenChange }: CompareDrawerProps) {
  const selectedRuns = useMemo(
    () => selection.map((id) => runs.find((run) => run.runId === id)).filter(Boolean) as AnalysisRunResult[],
    [runs, selection],
  );

  const toggleRun = (runId: string) => {
    if (selection.includes(runId)) {
      onSelectionChange(selection.filter((id) => id !== runId));
      return;
    }

    const next = [...selection, runId].slice(-2);
    onSelectionChange(next);
  };

  const [left, right] = selectedRuns;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-xl">
        <SheetHeader>
          <SheetTitle>Compare analysis runs</SheetTitle>
          <SheetDescription>
            Select up to two runs to compare their metadata and headline statistics.
          </SheetDescription>
        </SheetHeader>

        <div className="my-4 space-y-3">
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No analysis runs available yet.</p>
          ) : (
            <div className="space-y-3">
              {runs
                .slice()
                .reverse()
                .map((run) => {
                  const checked = selection.includes(run.runId);
                  return (
                    <label
                      key={run.runId}
                      className="flex items-start gap-3 rounded-lg border border-border/60 bg-background/60 p-3 text-sm text-foreground"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleRun(run.runId)}
                        className="mt-0.5"
                      />
                      <span className="flex flex-col">
                        <span className="font-medium">{run.templateId}</span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(run.finishedAt).toLocaleString()} · {(run.durationMs / 1000).toFixed(1)}s
                        </span>
                      </span>
                    </label>
                  );
                })}
            </div>
          )}
        </div>

        {selectedRuns.length === 2 ? (
          <div className="mt-6 space-y-4">
            <h3 className="text-sm font-semibold text-foreground">Summary</h3>
            <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Metric</span>
              <span className="font-medium text-foreground">{left.templateId}</span>
              <span className="font-medium text-foreground">{right.templateId}</span>

              <span>Finished at</span>
              <span>{new Date(left.finishedAt).toLocaleString()}</span>
              <span>{new Date(right.finishedAt).toLocaleString()}</span>

              <span>Duration (s)</span>
              <span>{(left.durationMs / 1000).toFixed(1)}</span>
              <span>{(right.durationMs / 1000).toFixed(1)}</span>

              <span>Tables</span>
              <span>{left.tables.length}</span>
              <span>{right.tables.length}</span>

              <span>Charts</span>
              <span>{left.charts.length}</span>
              <span>{right.charts.length}</span>
            </div>
            <div className="space-y-2 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Notes</p>
              <div className="rounded-md border border-border/60 bg-background/40 p-2">
                <p className="text-xs text-foreground">{left.notes ?? 'No notes recorded.'}</p>
              </div>
              <div className="rounded-md border border-border/60 bg-background/40 p-2">
                <p className="text-xs text-foreground">{right.notes ?? 'No notes recorded.'}</p>
              </div>
            </div>
          </div>
        ) : null}

        <SheetFooter className="mt-6">
          <SheetClose asChild>
            <Button variant="outline">Close</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
