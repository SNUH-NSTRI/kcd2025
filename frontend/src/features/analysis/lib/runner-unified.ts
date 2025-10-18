/**
 * Unified runner that supports both local simulation and API modes
 */

import { simulateAnalysisRun } from './runner';
import { runAnalysisViaAPI } from './runner-api';
import type {
  AnalysisRunResult,
  AnalysisTemplateMeta,
  CohortResult,
} from '@/features/flow/types';

export type RunMode = 'simulation' | 'api';

interface UnifiedRunParams {
  template: AnalysisTemplateMeta;
  cohort: CohortResult;
  runId: string;
  startedAt: string;
  projectId: string;
  mode?: RunMode;
  onProgress: (value: number) => void;
  onComplete: (result: AnalysisRunResult) => void;
  onError: (error: Error) => void;
  onCancel?: () => void;
}

/**
 * Run analysis using selected mode
 * Defaults to simulation mode for backward compatibility
 */
export function runAnalysis({
  mode = 'simulation',
  ...params
}: UnifiedRunParams) {
  if (mode === 'api') {
    return runAnalysisViaAPI(params);
  }

  // Fallback to local simulation
  return simulateAnalysisRun(params);
}

/**
 * Get the appropriate run mode based on environment
 */
export function getDefaultRunMode(): RunMode {
  // Check if API URL is configured
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl && apiUrl !== 'http://localhost:8000') {
    return 'api';
  }

  // Default to simulation for local development
  return 'simulation';
}

