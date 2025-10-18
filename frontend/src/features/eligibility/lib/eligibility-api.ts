/**
 * Eligibility Extraction API client
 *
 * Provides type-safe methods for interacting with the eligibility extraction endpoints.
 */

import { apiClient, ApiResponse } from "@/remote/client";
import type {
  ExtractRequest,
  ExtractResponse,
  ReviewRequest,
  ReviewResponse,
  CorrectionStats,
  CorrectionHistory,
} from "../types";

export const eligibilityApi = {
  /**
   * Extract eligibility criteria from NCT data.
   *
   * Workflow:
   * 1. Fetches NCT data from ClinicalTrials.gov
   * 2. Selects relevant few-shot examples
   * 3. Calls LLM to extract structured criteria
   * 4. Returns extraction with confidence score
   *
   * @param request Request containing NCT ID
   * @returns Extraction result with examples used
   */
  extract: async (request: ExtractRequest) => {
    return apiClient.post<ApiResponse<ExtractResponse>>(
      "/api/eligibility/extract",
      request
    );
  },

  /**
   * Submit review/correction for an extraction.
   *
   * Actions:
   * - "accept": Accept extraction as-is (no correction saved)
   * - "edit": Submit corrected extraction with keywords
   *
   * @param request Review request with action and optional corrections
   * @returns Review result with quality score
   */
  review: async (request: ReviewRequest) => {
    return apiClient.post<ApiResponse<ReviewResponse>>(
      "/api/eligibility/review",
      request
    );
  },

  /**
   * Get correction statistics.
   *
   * Returns:
   * - Total corrections and trials
   * - Average quality score
   * - Corrections by condition/keyword
   * - Recent corrections
   *
   * @returns Aggregated statistics
   */
  getStats: async () => {
    return apiClient.get<ApiResponse<CorrectionStats>>(
      "/api/eligibility/corrections/stats"
    );
  },

  /**
   * Get correction history for a specific NCT ID.
   *
   * Returns all versions of corrections for the given trial.
   *
   * @param nctId NCT ID to query
   * @returns Correction history with all versions
   */
  getHistory: async (nctId: string) => {
    return apiClient.get<ApiResponse<CorrectionHistory>>(
      `/api/eligibility/corrections/${nctId}`
    );
  },
};
