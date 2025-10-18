'use client';

/**
 * React Query hooks for pipeline API operations
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { pipelineApi, workspaceApi } from '@/remote';
import type {
  SearchLitRequest,
  ParseTrialsRequest,
  MapToEHRRequest,
  FilterCohortRequest,
  AnalyzeRequest,
  WriteReportRequest,
  RunAllRequest,
} from '@/remote/types/pipeline';

/**
 * Hook for literature search
 */
export function useSearchLiterature() {
  return useMutation({
    mutationFn: (request: SearchLitRequest) =>
      pipelineApi.searchLiterature(request),
  });
}

/**
 * Hook for trial parsing
 */
export function useParseTrials() {
  return useMutation({
    mutationFn: (request: ParseTrialsRequest) =>
      pipelineApi.parseTrials(request),
  });
}

/**
 * Hook for EHR mapping
 */
export function useMapToEHR() {
  return useMutation({
    mutationFn: (request: MapToEHRRequest) => pipelineApi.mapToEHR(request),
  });
}

/**
 * Hook for cohort filtering
 */
export function useFilterCohort() {
  return useMutation({
    mutationFn: (request: FilterCohortRequest) =>
      pipelineApi.filterCohort(request),
  });
}

/**
 * Hook for outcome analysis
 */
export function useAnalyzeOutcomes() {
  return useMutation({
    mutationFn: (request: AnalyzeRequest) =>
      pipelineApi.analyzeOutcomes(request),
  });
}

/**
 * Hook for report generation
 */
export function useWriteReport() {
  return useMutation({
    mutationFn: (request: WriteReportRequest) =>
      pipelineApi.writeReport(request),
  });
}

/**
 * Hook for full pipeline execution
 */
export function useRunAllPipeline() {
  return useMutation({
    mutationFn: (request: RunAllRequest) => pipelineApi.runAll(request),
  });
}

/**
 * Hook to fetch analysis results
 */
export function useAnalysisData(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['analysis', projectId],
    queryFn: () => workspaceApi.getAnalysis(projectId),
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

