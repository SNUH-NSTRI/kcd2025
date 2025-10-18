'use client';

/**
 * React Query hooks for cohort operations
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { workspaceApi, pipelineApi } from '@/remote';
import type { FilterCohortRequest } from '@/remote/types/pipeline';

/**
 * Hook to fetch cohort data
 */
export function useCohortData(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['cohort', projectId],
    queryFn: () => workspaceApi.getCohort(projectId),
    enabled,
  });
}

/**
 * Hook to fetch cohort summary
 */
export function useCohortSummary(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['cohort-summary', projectId],
    queryFn: () => workspaceApi.getCohortSummary(projectId),
    enabled,
  });
}

/**
 * Hook to generate cohort
 */
export function useGenerateCohort() {
  return useMutation({
    mutationFn: (request: FilterCohortRequest) =>
      pipelineApi.filterCohort(request),
  });
}

