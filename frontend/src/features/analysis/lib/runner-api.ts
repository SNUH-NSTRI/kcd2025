/**
 * API-based analysis runner
 * Replaces local simulation with backend API calls
 */

import { pipelineApi } from '@/remote';
import type {
  AnalysisRunResult,
  AnalysisTemplateMeta,
  CohortResult,
} from '@/features/flow/types';

interface RunAnalysisParams {
  template: AnalysisTemplateMeta;
  cohort: CohortResult;
  runId: string;
  startedAt: string;
  projectId: string;
  onProgress: (value: number) => void;
  onComplete: (result: AnalysisRunResult) => void;
  onError: (error: Error) => void;
  onCancel?: () => void;
}

/**
 * Run analysis using backend API
 */
export async function runAnalysisViaAPI({
  template,
  cohort,
  runId,
  startedAt,
  projectId,
  onProgress,
  onComplete,
  onError,
  onCancel,
}: RunAnalysisParams) {
  let cancelled = false;

  // Progress simulation while waiting for API
  const progressInterval = setInterval(() => {
    if (cancelled) return;
    // Simulate progress (will be replaced by WebSocket in future)
    const currentProgress = Math.min(90, Math.random() * 100);
    onProgress(currentProgress);
  }, 500);

  try {
    // Call backend API for analysis
    // Using hardcoded defaults since template doesn't contain these fields
    const response = await pipelineApi.analyzeOutcomes({
      project_id: projectId,
      treatment_column: 'on_arnI',
      outcome_column: 'mortality_30d',
      estimators: ['synthetic'],
    });

    if (cancelled) {
      clearInterval(progressInterval);
      onCancel?.();
      return;
    }

    clearInterval(progressInterval);
    onProgress(100);

    // Transform API response to match expected result format
    // TODO: Map response.data to proper tables and charts format
    const result: AnalysisRunResult = {
      runId,
      templateId: template.id,
      startedAt,
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - new Date(startedAt).getTime(),
      tables: [], // TODO: Transform response.data.metrics to tables
      charts: [], // TODO: Transform response.data to charts
      notes: `Analysis completed. Outcome count: ${response.data?.outcome_count || 0}`,
    };

    onComplete(result);
  } catch (error) {
    clearInterval(progressInterval);
    onError(
      error instanceof Error ? error : new Error('Analysis execution failed')
    );
  }

  return () => {
    cancelled = true;
    clearInterval(progressInterval);
    onCancel?.();
  };
}

