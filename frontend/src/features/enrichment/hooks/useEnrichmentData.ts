/**
 * React Query hook for fetching trial enrichment data
 */

import { useQuery } from '@tanstack/react-query';
import { fetchEnrichmentData } from '../api';

/**
 * React Query hook to fetch and manage enrichment data for a specific trial.
 *
 * @param nctId - The NCT ID of the trial (e.g., "NCT03389555")
 * @returns The result of the React Query operation with data, loading, error states
 */
export function useEnrichmentData(nctId: string) {
  return useQuery({
    queryKey: ['enrichment', nctId],
    queryFn: () => fetchEnrichmentData(nctId),
    enabled: !!nctId && /^NCT\d{8}$/i.test(nctId), // Only run if valid NCT ID format
    staleTime: 1000 * 60 * 5, // Cache data for 5 minutes
    retry: 1, // Retry once on failure
  });
}
