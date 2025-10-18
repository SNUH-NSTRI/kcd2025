'use client';

/**
 * React Query hooks for schema operations
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { workspaceApi, pipelineApi } from '@/remote';
import type { ParseTrialsRequest, MapToEHRRequest } from '@/remote/types/pipeline';

/**
 * Hook to fetch trial schema
 */
export function useTrialSchema(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['schema', projectId],
    queryFn: () => workspaceApi.getSchema(projectId),
    enabled,
  });
}

/**
 * Hook to parse trials and generate schema
 */
export function useParseTrials() {
  return useMutation({
    mutationFn: (request: ParseTrialsRequest) =>
      pipelineApi.parseTrials(request),
  });
}

/**
 * Hook to map schema to EHR
 */
export function useMapToEHR() {
  return useMutation({
    mutationFn: (request: MapToEHRRequest) => pipelineApi.mapToEHR(request),
  });
}

/**
 * Hook to fetch filter specification
 */
export function useFilterSpec(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['filter-spec', projectId],
    queryFn: () => workspaceApi.getFilterSpec(projectId),
    enabled,
  });
}

