'use client';

/**
 * React Query hooks for literature search operations
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { workspaceApi, pipelineApi } from '@/remote';
import type { SearchLitRequest } from '@/remote/types/pipeline';

/**
 * Hook to fetch literature corpus
 */
export function useLiteratureCorpus(projectId: string, enabled = true) {
  return useQuery({
    queryKey: ['corpus', projectId],
    queryFn: () => workspaceApi.getCorpus(projectId),
    enabled,
  });
}

/**
 * Hook to search literature
 */
export function useSearchLiterature() {
  return useMutation({
    mutationFn: (request: SearchLitRequest) =>
      pipelineApi.searchLiterature(request),
  });
}

