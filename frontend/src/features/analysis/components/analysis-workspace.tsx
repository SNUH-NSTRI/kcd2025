'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import { useAnalysisState, useCohortState, useFlow } from '@/features/flow/context';
import { generateRunId } from '../lib/id';
import { simulateAnalysisRun } from '../lib/runner';
import { TemplatePicker } from './template-picker';
import { RunPanel } from './run-panel';
import { ResultViewer } from './result-viewer';
import { CompareDrawer } from './compare-drawer';
import { StatisticianPanel } from './statistician-panel';
import type { AnalysisRunProgress } from '@/features/flow/types';
import { useAudit } from '@/features/audit';

export function AnalysisWorkspace() {
  const { toast } = useToast();
  const {
    state,
    selectAnalysisTemplate,
    startAnalysisRun,
    updateAnalysisProgress,
    completeAnalysisRun,
    failAnalysisRun,
    cancelAnalysisRun,
    setAnalysisCompareSelection,
    markDone,
  } = useFlow();
  const analysisState = useAnalysisState();
  const cohortState = useCohortState();
  const cancelRef = useRef<(() => void) | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const { createEvent } = useAudit();

  const selectedTemplate = useMemo(
    () => analysisState.templates.find((template) => template.id === analysisState.selectedTemplateId) ?? null,
    [analysisState.templates, analysisState.selectedTemplateId],
  );

  const cohortReady = Boolean(cohortState.result);

  const lastRun = analysisState.history.slice(-1)[0] ?? null;

  const handleStart = useCallback(() => {
    if (analysisState.activeRun) {
      toast({
        title: 'Analysis already running',
        description: 'Cancel the current run before starting a new one.',
        variant: 'destructive',
      });
      return;
    }

    if (!selectedTemplate) {
      toast({
        title: 'Select a template',
        description: 'Choose an analysis template to run.',
        variant: 'destructive',
      });
      return;
    }

    if (!cohortState.result) {
      toast({
        title: 'Generate a cohort first',
        description: 'Create a cohort before running analyses.',
        variant: 'destructive',
      });
      return;
    }

    const runId = generateRunId();
    const startedAt = new Date().toISOString();
    const run: AnalysisRunProgress = {
      runId,
      templateId: selectedTemplate.id,
      startedAt,
      status: 'running',
      progress: 0,
    };

    startAnalysisRun(run);
    updateAnalysisProgress(runId, 5);
    createEvent('analysis.run.started', 'analysis', {
      summary: `Started ${selectedTemplate.name} analysis run.`,
      templateId: selectedTemplate.id,
      runId,
    });

    cancelRef.current = simulateAnalysisRun({
      template: selectedTemplate,
      cohort: cohortState.result,
      runId,
      startedAt,
      onProgress: (progress) => updateAnalysisProgress(runId, progress),
      onComplete: (result) => {
        cancelRef.current = null;
        completeAnalysisRun(result);
        toast({
          title: 'Analysis completed',
          description: `${selectedTemplate.name} finished in ${(result.durationMs / 1000).toFixed(1)} seconds.`,
        });
        if (state.steps.analysis !== 'done') {
          markDone('analysis');
        }
        createEvent('analysis.run.completed', 'analysis', {
          summary: `${selectedTemplate.name} completed successfully.`,
          runId: result.runId,
          templateId: selectedTemplate.id,
          durationMs: result.durationMs,
        });
      },
      onError: (error) => {
        cancelRef.current = null;
        failAnalysisRun(runId, error.message);
        toast({
          title: 'Analysis failed',
          description: error.message,
          variant: 'destructive',
        });
        createEvent('analysis.run.failed', 'analysis', {
          summary: `${selectedTemplate.name} failed to complete.`,
          runId,
          templateId: selectedTemplate.id,
          error: error.message,
        });
      },
      onCancel: () => {
        cancelRef.current = null;
        cancelAnalysisRun(runId);
        toast({
          title: 'Analysis cancelled',
          description: 'The analysis run was stopped.',
        });
        createEvent('analysis.run.cancelled', 'analysis', {
          summary: `${selectedTemplate.name} run was cancelled.`,
          runId,
          templateId: selectedTemplate.id,
        });
      },
    });
  }, [
    analysisState.activeRun,
    cancelAnalysisRun,
    createEvent,
    cohortState.result,
    completeAnalysisRun,
    failAnalysisRun,
    markDone,
    selectedTemplate,
    startAnalysisRun,
    state.steps.analysis,
    toast,
    updateAnalysisProgress,
  ]);

  const handleCancel = useCallback(() => {
    if (!analysisState.activeRun) return;
    cancelRef.current?.();
    cancelRef.current = null;
  }, [analysisState.activeRun]);

  const handleSelectTemplate = useCallback(
    (templateId: string) => selectAnalysisTemplate(templateId),
    [selectAnalysisTemplate],
  );

  const handleCompareToggle = useCallback(() => setCompareOpen((prev) => !prev), []);

  const canRun = Boolean(selectedTemplate && cohortReady && !analysisState.activeRun);

  useEffect(
    () => () => {
      cancelRef.current?.();
      cancelRef.current = null;
    },
    [],
  );

  return (
    <div className="space-y-6">
      <TemplatePicker
        templates={analysisState.templates}
        selectedId={analysisState.selectedTemplateId}
        onSelect={handleSelectTemplate}
        disabled={Boolean(analysisState.activeRun)}
      />

      <RunPanel
        activeRun={analysisState.activeRun}
        onRun={handleStart}
        onCancel={handleCancel}
        canRun={canRun}
        templateName={selectedTemplate?.name ?? null}
        cohortReady={cohortReady}
        lastRun={lastRun}
      />

      {/* Statistician Agent Panel - Always visible for NCT03389555 */}
      <StatisticianPanel
        nctId={(state.mode === 'demo' && state.demoConfig?.nctId) || "NCT03389555"}
        medication="hydrocortisone na succ."
        onComplete={(result) => {
          toast({
            title: 'Agent completed',
            description: 'Statistician agent analysis finished successfully',
          });
          if (state.steps.analysis !== 'done') {
            markDone('analysis');
          }
        }}
      />

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">History</h3>
        <button
          type="button"
          className="rounded-full border border-border/70 px-3 py-1 text-xs text-muted-foreground transition hover:border-primary hover:text-primary"
          onClick={handleCompareToggle}
          disabled={analysisState.history.length < 2}
        >
          Compare runs
        </button>
      </div>

      <div className="space-y-3">
        {analysisState.history.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No completed runs yet. Execute an analysis to populate history.
          </p>
        ) : (
          analysisState.history
            .slice()
            .reverse()
            .map((run) => (
              <div
                key={run.runId}
                className="flex flex-wrap items-center justify-between rounded-lg border border-border/60 bg-card/60 px-4 py-3 text-sm"
              >
                <div className="flex flex-col">
                  <span className="font-medium text-foreground">{run.templateId}</span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(run.finishedAt).toLocaleString()} · {(run.durationMs / 1000).toFixed(1)}s
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Tables {run.tables.length}</span>
                  <span>Charts {run.charts.length}</span>
                </div>
              </div>
            ))
        )}
      </div>

      <ResultViewer result={lastRun ?? null} />

      <CompareDrawer
        runs={analysisState.history}
        selection={analysisState.compareSelection}
        onSelectionChange={setAnalysisCompareSelection}
        open={compareOpen}
        onOpenChange={setCompareOpen}
      />
    </div>
  );
}
