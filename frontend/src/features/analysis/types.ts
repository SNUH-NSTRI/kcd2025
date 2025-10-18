import type {
  AnalysisChart,
  AnalysisRunProgress,
  AnalysisRunResult,
  AnalysisTable,
  AnalysisTemplateMeta,
} from '@/features/flow/types';

export type {
  AnalysisChart,
  AnalysisRunProgress,
  AnalysisRunResult,
  AnalysisTable,
  AnalysisTemplateMeta,
};

export interface AnalysisRunnerOptions {
  template: AnalysisTemplateMeta;
  seed: string;
  cohortSize: number;
  onProgress: (percent: number) => void;
  onComplete: (result: AnalysisRunResult) => void;
  onError: (error: Error) => void;
  onCancel?: () => void;
}
