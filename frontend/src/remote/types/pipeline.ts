/**
 * Type definitions for pipeline API
 */

import type { DemoStageResult } from '@/features/flow/types';

export interface SearchLitRequest {
  project_id: string;
  disease_code: string;
  keywords: string[];
  sources: string[];
  max_records?: number;
  require_full_text?: boolean;
  impl?: string;
}

export interface ParseTrialsRequest {
  project_id: string;
  llm_provider?: string;
  prompt_template?: string;
  impl?: string;
}

export interface MapToEHRRequest {
  project_id: string;
  ehr_source?: string;
  dictionary?: string;
  output_format?: "json" | "sql";
  impl?: string;
}

export interface FilterCohortRequest {
  project_id: string;
  input_uri?: string;
  sample_size?: number;
  dry_run?: boolean;
  impl?: string;
}

export interface AnalyzeRequest {
  project_id: string;
  treatment_column?: string;
  outcome_column?: string;
  estimators: string[];
  impl?: string;
}

export interface WriteReportRequest {
  project_id: string;
  template: string;
  format?: "markdown" | "pdf";
  hil_review?: boolean;
  impl?: string;
}

export interface StimulaRequest {
  project_id: string;
  vary?: string[];
  max_variations?: number;
  subject_id?: string;
}

export interface RunAllRequest {
  project_id: string;
  disease_code: string;
  keywords: string[];
  sources: string[];
  max_records?: number;
  require_full_text?: boolean;
  llm_provider?: string;
  prompt_template?: string;
  ehr_source?: string;
  dictionary?: string;
  filters_format?: "json" | "sql";
  input_uri?: string;
  sample_size?: number;
  treatment_column?: string;
  outcome_column?: string;
  estimators: string[];
  template: string;
  report_format?: "markdown" | "pdf";
  impl_overrides?: Record<string, string>;
}

export interface SearchLitResult {
  document_count: number;
  documents: Array<{
    source: string;
    identifier: string;
    title: string;
    has_full_text: boolean;
  }>;
}

export interface ParseTrialsResult {
  disease_code: string;
  inclusion_count: number;
  exclusion_count: number;
  feature_count: number;
}

export interface MapToEHRResult {
  ehr_source: string;
  variable_map_count: number;
  inclusion_filters_count: number;
  exclusion_filters_count: number;
}

export interface FilterCohortResult {
  total_subjects: number;
  summary: Record<string, unknown>;
}

export interface AnalyzeResult {
  metrics: Record<string, unknown>;
  outcome_count: number;
}

export interface WriteReportResult {
  report_body_length: number;
  figure_count: number;
}

export interface StimulaResult {
  scenario_count: number;
  baseline_subjects: number;
}

export interface RunAllResult {
  literature: SearchLitResult;
  parsing: ParseTrialsResult;
  mapping: MapToEHRResult;
  cohort: FilterCohortResult;
  analysis: AnalyzeResult;
  report: WriteReportResult;
}

// Demo Mode API Types
export interface DemoRunRequest {
  project_id: string;
  nct_id: string;
  sample_size?: number;
  treatment_column?: string;
  outcome_column?: string;
  estimators?: string[];
}

export interface DemoRunResult {
  status: 'success' | 'error';
  message: string;
  stages: {
    search_lit: DemoStageResult;
    parse_trials: DemoStageResult;
    filter_cohort: DemoStageResult;
    analyze: DemoStageResult;
  };
  execution_time_ms: number;
}

