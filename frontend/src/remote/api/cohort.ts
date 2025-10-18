/**
 * Cohort Quality Assessment API client
 */

import { apiClient, ApiResponse } from "../client";
import type {
  CohortQualityRequest,
  CohortQualityResult,
} from "../types/cohort";

export const cohortApi = {
  /**
   * Assess cohort quality through baseline balance and characterization.
   *
   * Part 1: Baseline Covariate Balance - Compare Treatment vs Control groups
   * Part 2: Cohort Characterization - Descriptive statistics for entire cohort
   *
   * @param request Request containing nct_id and medication
   * @returns Quality assessment with summary, baseline_balance, and cohort_characteristics
   */
  assessQuality: async (request: CohortQualityRequest) => {
    return apiClient.post<ApiResponse<CohortQualityResult>>(
      "/api/cohort/assess-quality",
      request
    );
  },

  /**
   * Fetch a limited sample of patients from the cohort for preview.
   *
   * @param nctId NCT ID of the study
   * @param medication Medication name
   * @param limit Number of patients to fetch (default: 10)
   * @returns Sample patient records
   */
  getSamplePatients: async (nctId: string, medication: string, limit: number = 10) => {
    return apiClient.post<ApiResponse<{
      patients: Array<{
        subject_id: number;
        age_at_admission: number;
        gender: string;
        treatment_group: number;
        icu_intime: string;
        icu_outtime: string;
        los: number;
        any_vasopressor: number;
        mortality: number;
      }>;
      count: number;
      limit: number;
    }>>(
      "/api/cohort/sample-patients",
      { nct_id: nctId, medication, limit }
    );
  },

  /**
   * Get real-time cohort summary statistics.
   * Calculated on-the-fly from CSV (~50ms for 11k patients)
   *
   * @param nctId NCT ID of the study
   * @param medication Medication name
   * @returns Real-time computed attrition and characteristics
   */
  getSummary: async (nctId: string, medication: string) => {
    return apiClient.post<ApiResponse<{
      attrition: {
        total: number;
        treatment: number;
        control: number;
        funnel: Array<{
          step: number;
          criteriaId: string;
          criteria_type?: string;
          description: string;
          patients_remaining: number;
          patients_excluded?: number;
          exclusion_reason?: string | null;
        }>;
        initial_count: number;
      };
      characteristics: {
        age: {
          mean: number;
          std: number;
          median: number;
          min: number;
          max: number;
        };
        gender: {
          M: number;
          F: number;
        };
        mortality_rate: number;
        vasopressor_rate: number;
      };
    }>>(
      "/api/cohort/summary",
      { nct_id: nctId, medication }
    );
  },
};
