/**
 * Projects API client
 */

import { apiClient, API_BASE_URL } from "../client";
import type { ProjectListResponse, ProjectInfo } from "../types/workspace";

export const projectsApi = {
  /**
   * List all projects in workspace
   */
  listProjects: async () => {
    return apiClient.get<ProjectListResponse>("/api/projects");
  },

  /**
   * Get detailed information about a specific project
   */
  getProject: async (projectId: string) => {
    return apiClient.get<ProjectInfo>(`/api/projects/${projectId}`);
  },

  /**
   * Get cohort CSV data for a specific NCT ID and medication
   */
  getCohortData: async (nctId: string, medication: string) => {
    const url = `${API_BASE_URL}/api/projects/${nctId}/cohorts/${medication}/data`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch cohort data: ${response.statusText}`);
    }
    const csvText = await response.text();
    return csvText;
  },
};

