/**
 * Agent API Types
 *
 * TypeScript types matching backend Pydantic schemas for agent system.
 * Backend schemas: backend/src/rwe_api/schemas/agents.py
 */

/**
 * Agent execution status
 */
export enum AgentStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

/**
 * Agent metadata
 */
export interface AgentMetadata {
  name: string;
  version: string;
  description: string;
}

/**
 * List all available agents response
 */
export interface AgentListResponse {
  agents: AgentMetadata[];
}

/**
 * Request to run an agent
 */
export interface AgentRunRequest {
  agent_name: string;
  nct_id: string;
  medication: string;
  config_overrides?: Record<string, any>;
}

/**
 * Response when starting an agent execution
 */
export interface AgentRunResponse {
  job_id: string;
  agent_name: string;
  status: AgentStatus;
  message: string;
}

/**
 * Job status polling response
 */
export interface JobStatusResponse {
  job_id: string;
  status: AgentStatus;
  progress?: string;
  result?: AgentResult;
  error?: string;
}

/**
 * Agent execution result
 */
export interface AgentResult {
  success: boolean;
  output: Record<string, any>;
  output_dir?: string; // Directory where agent outputs are stored
  metadata?: Record<string, any>;
  error?: string;
}

/**
 * Visualization file paths for Statistician Agent output
 */
export interface StatisticianVisualizations {
  baseline_table_main: string;
  baseline_table_sensitivity: string;
  love_plot_main: string;  // SMD plot (Standardized Mean Difference)
  love_plot_sensitivity: string;  // SMD plot (Standardized Mean Difference)
  kaplan_meier_main: string;  // Kaplan-Meier survival curve
  kaplan_meier_sensitivity: string;  // Kaplan-Meier survival curve
}

/**
 * Statistician Agent specific result output
 */
export interface StatisticianOutput {
  cohort_summary: {
    total_patients: number;
    treatment_n: number;
    control_n: number;
    treatment_pct: number;
    mortality_overall?: number;
  };
  baseline_imbalance: {
    total_variables: number;
    imbalanced_vars: number;
    max_smd: number;
    median_smd: number;
    top_imbalanced: Array<{
      variable: string;
      smd: number;
      treatment_mean: number;
      control_mean: number;
      imbalanced: boolean;
    }>;
  };
  missingness_report: {
    high_missing_count: number;
    high_missing_vars: Record<string, number>;
    median_missing_pct: number;
  };
  psm_params: {
    caliper_multiplier: number;
    matching_ratio: string;
    variable_selection_strategy: string;
    exclude_threshold_pct: number;
    rationale: string;
  };
  psm_results: {
    main_analysis: SurvivalSummary;
    sensitivity_analysis: SurvivalSummary;
    output_dir: string;
  };
  visualizations?: StatisticianVisualizations;  // NEW: Explicit paths to generated visualizations
  interpretation?: string; // Optional: Structured summary (no LLM)
  structured_summary?: {
    main_analysis: {
      matched_pairs: number;
      hazard_ratio: number;
      ci_95_lower: number;
      ci_95_upper: number;
      p_value: number;
      mortality_treatment_pct: number;
      mortality_control_pct: number;
    };
    sensitivity_analysis: {
      matched_pairs: number;
      hazard_ratio: number;
      ci_95_lower: number;
      ci_95_upper: number;
      p_value: number;
      mortality_treatment_pct: number;
      mortality_control_pct: number;
    };
    psm_quality: {
      caliper_multiplier: number;
      matching_ratio: string;
      variable_selection_strategy: string;
      pre_matching_max_smd: number;
      imbalanced_vars: number;
      total_vars: number;
    };
  };
  llm_summary?: {
    question?: string;
    conclusion?: string;
    population?: {
      total_patients: number;
      treatment_n: number;
      control_n: number;
      description: string;
    };
    intervention?: {
      treatment_group: string;
      control_group: string;
      primary_outcome: string;
    };
    findings?: {
      cox_hazard_ratio: number;
      ci_95: string;
      p_value: number;
      absolute_risk_difference: string;
      hazard_change: string;
      significance: string;
    };
  };
  output_dir: string;
}

/**
 * Survival analysis summary
 */
export interface SurvivalSummary {
  n_treatment?: number;
  n_control?: number;
  mortality_treatment?: number;
  mortality_control?: number;
  cox_hr?: number;
  cox_ci_lower?: number;
  cox_ci_upper?: number;
  cox_pvalue?: number;
}
