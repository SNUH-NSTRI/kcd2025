/**
 * API-based cohort generator
 * Replaces local synthesis with backend API calls
 */

import { pipelineApi } from '@/remote';
import type { CohortResult, CohortDatasetId } from '@/features/flow/types';
import type { TrialVariable } from '@/features/schema/types';

interface GenerateCohortParams {
  variables: TrialVariable[];
  mapping: Record<string, string | null>;
  cohortSize: number;
  seed: string;
  datasetId: CohortDatasetId;
  projectId: string;
}

/**
 * Generate cohort using backend API
 */
export async function generateCohortViaAPI({
  variables,
  mapping,
  cohortSize,
  seed,
  datasetId,
  projectId,
}: GenerateCohortParams): Promise<CohortResult> {
  try {
    // Call backend API for cohort filtering
    const response = await pipelineApi.filterCohort({
      project_id: projectId,
      input_uri: 'duckdb:///synthetic.duckdb',
      sample_size: cohortSize,
      dry_run: false,
    });

    if (response.status !== 'success') {
      throw new Error(response.error || 'Cohort generation failed');
    }

    // Transform API response to match expected format
    // Note: This is a simplified transformation
    // In production, you'd need proper data mapping
    const result: CohortResult = {
      patients: [], // Will be populated from workspace API
      summary: {
        size: response.data?.total_subjects || 0,
        age: { mean: 0, median: 0, min: 0, max: 0, histogram: [] },
        sex: { counts: { M: 0, F: 0 }, proportions: { M: 0, F: 0 } },
        datasetId: datasetId,
      },
      createdAt: new Date().toISOString(),
      seed: `${seed}|${datasetId}`,
    };

    return result;
  } catch (error) {
    throw error instanceof Error
      ? error
      : new Error('Failed to generate cohort via API');
  }
}

/**
 * Auto-suggest mappings (kept as local logic for performance)
 */
export function suggestMappingsAPI(
  variables: TrialVariable[]
): Record<string, string> {
  // This logic is kept local as it's just a UI convenience feature
  // and doesn't require backend processing
  const suggestions: Record<string, string> = {};

  variables.forEach((variable) => {
    const normalized = variable.name.toLowerCase();
    // Simple keyword matching
    if (normalized.includes('age')) suggestions[variable.id] = 'age';
    if (normalized.includes('sex') || normalized.includes('gender'))
      suggestions[variable.id] = 'sex';
    if (normalized.includes('lvef')) suggestions[variable.id] = 'lvef';
    if (normalized.includes('bnp')) suggestions[variable.id] = 'bnp';
  });

  return suggestions;
}

