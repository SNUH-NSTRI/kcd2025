/**
 * Pipeline API client
 */

import { apiClient, ApiResponse } from "../client";
import type {
  SearchLitRequest,
  SearchLitResult,
  ParseTrialsRequest,
  ParseTrialsResult,
  MapToEHRRequest,
  MapToEHRResult,
  FilterCohortRequest,
  FilterCohortResult,
  AnalyzeRequest,
  AnalyzeResult,
  WriteReportRequest,
  WriteReportResult,
  StimulaRequest,
  StimulaResult,
  RunAllRequest,
  RunAllResult,
  DemoRunRequest,
  DemoRunResult,
} from "../types/pipeline";

export const pipelineApi = {
  /**
   * Execute literature search stage
   */
  searchLiterature: async (request: SearchLitRequest) => {
    return apiClient.post<ApiResponse<SearchLitResult>>(
      "/api/pipeline/search-lit",
      request
    );
  },

  /**
   * Execute trial parsing stage
   */
  parseTrials: async (request: ParseTrialsRequest) => {
    return apiClient.post<ApiResponse<ParseTrialsResult>>(
      "/api/pipeline/parse-trials",
      request
    );
  },

  /**
   * Execute EHR mapping stage
   */
  mapToEHR: async (request: MapToEHRRequest) => {
    return apiClient.post<ApiResponse<MapToEHRResult>>(
      "/api/pipeline/map-to-ehr",
      request
    );
  },

  /**
   * Execute cohort filtering stage
   */
  filterCohort: async (request: FilterCohortRequest) => {
    return apiClient.post<ApiResponse<FilterCohortResult>>(
      "/api/pipeline/filter-cohort",
      request
    );
  },

  /**
   * Execute outcome analysis stage
   */
  analyzeOutcomes: async (request: AnalyzeRequest) => {
    return apiClient.post<ApiResponse<AnalyzeResult>>(
      "/api/pipeline/analyze",
      request
    );
  },

  /**
   * Execute report generation stage
   */
  writeReport: async (request: WriteReportRequest) => {
    return apiClient.post<ApiResponse<WriteReportResult>>(
      "/api/pipeline/write-report",
      request
    );
  },

  /**
   * Execute what-if simulation
   */
  runStimula: async (request: StimulaRequest) => {
    return apiClient.post<ApiResponse<StimulaResult>>(
      "/api/pipeline/stimula",
      request
    );
  },

  /**
   * Execute full pipeline (all stages)
   */
  runAll: async (request: RunAllRequest) => {
    return apiClient.post<ApiResponse<RunAllResult>>(
      "/api/pipeline/run-all",
      request
    );
  },

  /**
   * Execute demo pipeline (bypasses search-lit and trialist)
   *
   * This endpoint is designed for datathon demonstrations where:
   * - Literature search and trialist stages use pre-built fixtures
   * - Cohort extraction and statistical analysis execute normally
   *
   * @param request Demo pipeline configuration
   * @returns Demo execution results with stage metadata
   */
  runDemo: async (request: DemoRunRequest) => {
    return apiClient.post<ApiResponse<DemoRunResult>>(
      "/api/pipeline/demo/run-all",
      request
    );
  },
};

