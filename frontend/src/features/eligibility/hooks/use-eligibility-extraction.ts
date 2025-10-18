'use client';

/**
 * React Query hooks for eligibility extraction operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { eligibilityApi } from '../lib/eligibility-api';
import type {
  ExtractRequest,
  ReviewRequest,
} from '../types';

/**
 * Hook to extract eligibility criteria from NCT data.
 *
 * Usage:
 * ```tsx
 * const { mutate, isPending, data } = useExtractEligibility();
 * mutate({ nct_id: "NCT03389555" });
 * ```
 */
export function useExtractEligibility() {
  return useMutation({
    mutationFn: (request: ExtractRequest) => eligibilityApi.extract(request),
  });
}

/**
 * Hook to submit review/correction for an extraction.
 *
 * Invalidates stats and history queries after successful submission.
 *
 * Usage:
 * ```tsx
 * const { mutate } = useReviewExtraction();
 * mutate({
 *   nct_id: "NCT03389555",
 *   action: "edit",
 *   original_extraction: {...},
 *   corrected_extraction: {...},
 *   keywords: ["age_criteria"],
 *   corrected_by: "user@example.com"
 * });
 * ```
 */
export function useReviewExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ReviewRequest) => eligibilityApi.review(request),
    onSuccess: (data, variables) => {
      // Invalidate stats to refresh dashboard
      queryClient.invalidateQueries({ queryKey: ['eligibility', 'stats'] });
      // Invalidate history for this specific NCT ID
      queryClient.invalidateQueries({
        queryKey: ['eligibility', 'history', variables.nct_id],
      });
    },
  });
}

/**
 * Hook to fetch correction statistics.
 *
 * Usage:
 * ```tsx
 * const { data, isLoading } = useCorrectionStats();
 * ```
 */
export function useCorrectionStats(enabled = true) {
  return useQuery({
    queryKey: ['eligibility', 'stats'],
    queryFn: () => eligibilityApi.getStats(),
    enabled,
  });
}

/**
 * Hook to fetch correction history for a specific NCT ID.
 *
 * Usage:
 * ```tsx
 * const { data } = useCorrectionHistory("NCT03389555");
 * ```
 */
export function useCorrectionHistory(nctId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['eligibility', 'history', nctId],
    queryFn: () => {
      if (!nctId) throw new Error('NCT ID is required');
      return eligibilityApi.getHistory(nctId);
    },
    enabled: enabled && !!nctId,
  });
}
