/**
 * Unified generator that supports both local synthesis and API modes
 */

import { generateCohort } from './generator';
import { generateCohortViaAPI } from './generator-api';
import type { CohortResult, CohortDatasetId } from '@/features/flow/types';
import type { TrialVariable } from '@/features/schema/types';

export type GeneratorMode = 'local' | 'api';

interface UnifiedGenerateParams {
  variables: TrialVariable[];
  mapping: Record<string, string | null>;
  cohortSize: number;
  seed: string;
  datasetId: CohortDatasetId;
  projectId: string;
  mode?: GeneratorMode;
}

/**
 * Generate cohort using selected mode
 * Defaults to local mode for backward compatibility
 */
export async function generateCohortUnified({
  mode = 'local',
  ...params
}: UnifiedGenerateParams): Promise<CohortResult> {
  if (mode === 'api') {
    return generateCohortViaAPI(params);
  }

  // Fallback to local synthesis
  return generateCohort(params);
}

/**
 * Get the appropriate generator mode based on environment
 */
export function getDefaultGeneratorMode(): GeneratorMode {
  // Check if API URL is configured
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl && apiUrl !== 'http://localhost:8000') {
    return 'api';
  }

  // Default to local for immediate feedback in development
  return 'local';
}

