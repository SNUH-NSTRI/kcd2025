import { synthesiseAnalysisResult } from './synthesise';
import type { AnalysisRunResult, AnalysisTemplateMeta, CohortResult } from '@/features/flow/types';

interface RunAnalysisParams {
  template: AnalysisTemplateMeta;
  cohort: CohortResult;
  runId: string;
  startedAt: string;
  onProgress: (value: number) => void;
  onComplete: (result: AnalysisRunResult) => void;
  onError: (error: Error) => void;
  onCancel?: () => void;
}

export function simulateAnalysisRun({
  template,
  cohort,
  runId,
  startedAt,
  onProgress,
  onComplete,
  onError,
  onCancel,
}: RunAnalysisParams) {
  const progressPhases = [12, 32, 54, 71, 88, 100];
  let cancelled = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let index = 0;

  const tick = () => {
    if (cancelled) return;

    if (index < progressPhases.length) {
      const value = progressPhases[index];
      onProgress(value);
      index += 1;
      if (value === 100) {
        try {
          const result = synthesiseAnalysisResult(template, cohort, runId, startedAt);
          onComplete(result);
        } catch (error) {
          onError(error instanceof Error ? error : new Error('Unknown analysis error'));
        }
        return;
      }
      timer = setTimeout(tick, 350);
      return;
    }
  };

  timer = setTimeout(tick, 250);

  return () => {
    if (cancelled) return;
    cancelled = true;
    if (timer) {
      clearTimeout(timer);
    }
    onCancel?.();
  };
}
