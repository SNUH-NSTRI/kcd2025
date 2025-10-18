/**
 * Enrichment API client for Stage 4 results
 */

import { apiClient, ApiResponse } from '@/remote/client';
import type { EnrichmentData } from './types';

export interface FetchEnrichmentRequest {
  project_id: string;
  nct_id: string;
}

export interface FetchEnrichmentResponse {
  status: string;
  message: string;
  schema: EnrichmentData;
}

/**
 * Fetches the enriched trial schema data for a given NCT ID.
 * This corresponds to the Stage 4 enrichment output with ICD codes and MIMIC mappings.
 *
 * @param nctId - The NCT ID of the trial to fetch (e.g., "NCT03389555")
 * @returns A promise that resolves to the enrichment data
 */
export async function fetchEnrichmentData(nctId: string): Promise<EnrichmentData> {
  try {
    const response = await apiClient.post<ApiResponse<FetchEnrichmentResponse>>(
      '/api/pipeline/parse-trials',
      {
        project_id: nctId.toLowerCase(),
        nct_id: nctId.toUpperCase(),
      }
    );

    if (response.data.status === 'success') {
      return response.data.data.schema;
    }

    throw new Error(response.data.message || 'Failed to fetch enrichment data');
  } catch (error: any) {
    console.error(`Failed to fetch enrichment data for ${nctId}:`, error);
    throw new Error(
      error.response?.data?.detail ||
        error.message ||
        `Could not retrieve enrichment results for trial ${nctId}.`
    );
  }
}
