/**
 * Workspace API client
 */

import { apiClient } from "../client";
import type {
  WorkspaceDataResponse,
  FileContentResponse,
  CohortSummary,
  AnalysisData,
} from "../types/workspace";

export const workspaceApi = {
  /**
   * Get workspace data for a specific project stage
   */
  getStageData: async (projectId: string, stage: string) => {
    return apiClient.get<WorkspaceDataResponse>(
      `/api/workspace/${projectId}/${stage}`
    );
  },

  /**
   * Read a specific file from workspace
   */
  getFileContent: async (projectId: string, stage: string, filename: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/${stage}/${filename}`
    );
  },

  /**
   * Get literature corpus for a project
   */
  getCorpus: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/corpus`
    );
  },

  /**
   * Get trial schema for a project
   */
  getSchema: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/schema`
    );
  },

  /**
   * Get filter specification for a project
   */
  getFilterSpec: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/filter-spec`
    );
  },

  /**
   * Get cohort data for a project
   */
  getCohort: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/cohort`
    );
  },

  /**
   * Get cohort summary for a project
   */
  getCohortSummary: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/cohort-summary`
    );
  },

  /**
   * Get analysis results for a project
   */
  getAnalysis: async (projectId: string) => {
    return apiClient.get<AnalysisData>(`/api/workspace/${projectId}/analysis`);
  },

  /**
   * Get report for a project
   */
  getReport: async (projectId: string) => {
    return apiClient.get<FileContentResponse>(
      `/api/workspace/${projectId}/report`
    );
  },
};

