/**
 * Agents API client
 *
 * Client for multi-agent system endpoints.
 * Provides access to intelligent agents like StatisticianAgent.
 */

import { apiClient, ApiResponse } from "../client";
import type {
  AgentListResponse,
  AgentRunRequest,
  AgentRunResponse,
  JobStatusResponse,
} from "../types/agents";

export const agentsApi = {
  /**
   * List all available agents
   *
   * @returns List of registered agents with metadata
   */
  listAgents: async () => {
    // Backend returns AgentListResponse directly (not wrapped)
    return apiClient.get<AgentListResponse>("/api/agents");
  },

  /**
   * Run an agent with specified parameters
   *
   * This starts an async background job and returns immediately with a job_id.
   * Use pollJobStatus() to check execution progress.
   *
   * @param agentName - Name of the agent to run (e.g., "statistician")
   * @param request - Agent execution parameters
   * @returns Job ID and initial status
   *
   * @example
   * ```typescript
   * const response = await agentsApi.runAgent("statistician", {
   *   agent_name: "statistician",
   *   nct_id: "NCT03389555",
   *   medication: "hydrocortisone na succ."
   * });
   * const jobId = response.data.job_id;
   * ```
   */
  runAgent: async (agentName: string, request: AgentRunRequest) => {
    // Backend returns AgentRunResponse directly (not wrapped)
    return apiClient.post<AgentRunResponse>(
      `/api/agents/${agentName}/run`,
      request
    );
  },

  /**
   * Poll job status
   *
   * Check the execution status of an agent job.
   * Call this periodically until status is "completed" or "failed".
   *
   * @param jobId - Job ID returned from runAgent()
   * @returns Current job status, progress, and result if completed
   *
   * @example
   * ```typescript
   * // Poll every 2 seconds
   * const interval = setInterval(async () => {
   *   const status = await agentsApi.pollJobStatus(jobId);
   *
   *   if (status.data.status === "completed") {
   *     console.log("Agent finished:", status.data.result);
   *     clearInterval(interval);
   *   } else if (status.data.status === "failed") {
   *     console.error("Agent failed:", status.data.error);
   *     clearInterval(interval);
   *   } else {
   *     console.log("Progress:", status.data.progress);
   *   }
   * }, 2000);
   * ```
   */
  pollJobStatus: async (jobId: string) => {
    // Backend returns JobStatusResponse directly (not wrapped)
    return apiClient.get<JobStatusResponse>(
      `/api/agents/jobs/${jobId}/status`
    );
  },

  /**
   * Run Statistician Agent (convenience method)
   *
   * Shorthand for running the statistician agent specifically.
   *
   * @param nctId - NCT trial ID (e.g., "NCT03389555")
   * @param medication - Treatment medication name
   * @param configOverrides - Optional config overrides
   * @returns Job ID and initial status
   *
   * @example
   * ```typescript
   * const response = await agentsApi.runStatistician(
   *   "NCT03389555",
   *   "hydrocortisone na succ."
   * );
   * ```
   */
  runStatistician: async (
    nctId: string,
    medication: string,
    configOverrides?: Record<string, any>
  ) => {
    return agentsApi.runAgent("statistician", {
      agent_name: "statistician",
      nct_id: nctId,
      medication,
      config_overrides: configOverrides,
    });
  },
};
