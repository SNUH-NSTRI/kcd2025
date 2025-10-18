import type { TrialSchema } from '@/features/schema/types';

export type Step = 'search' | 'schema' | 'cohort' | 'analysis' | 'report';

export type StepState = 'idle' | 'in-progress' | 'done' | 'error';

export type SourceFilter = 'all' | 'PubMed' | 'CTgov';

export type CohortDatasetId = 'mimic-iv' | 'k-mimic' | 'demo';

export type CohortSexCode = 'M' | 'F';

export interface CohortPatient {
  id: string;
  age: number;
  sex: CohortSexCode;
  vars: Record<string, unknown>;
}

export interface CohortAgeBucket {
  label: string;
  range: [number, number];
  count: number;
}

export interface CohortAgeSummary {
  mean: number;
  median: number;
  min: number;
  max: number;
  histogram: CohortAgeBucket[];
}

export interface CohortSexSummary {
  counts: Record<CohortSexCode, number>;
  proportions: Record<CohortSexCode, number>;
}

export interface CohortSummary {
  size: number;
  age: CohortAgeSummary;
  sex: CohortSexSummary;
  datasetId: CohortDatasetId;
}

export interface CohortResult {
  patients: CohortPatient[];
  summary: CohortSummary;
  createdAt: string;
  seed: string;
}

export interface CohortState {
  mapping: Record<string, string | null>;
  cohortSize: number;
  datasetId: CohortDatasetId;
  seed: string;
  result: CohortResult | null;
}

export interface AnalysisTemplateMeta {
  id: string;
  name: string;
  description: string;
  inputs: string[];
  outputs: string[];
}

export interface AnalysisChartPoint {
  x: number;
  y: number;
  lower?: number;
  upper?: number;
}

export interface AnalysisChart {
  id: string;
  type: 'line' | 'bar';
  title: string;
  series: Array<{
    id: string;
    label: string;
    points: AnalysisChartPoint[];
  }>;
  xLabel: string;
  yLabel: string;
}

export interface AnalysisTableRow {
  label: string;
  values: Record<string, string | number>;
}

export interface AnalysisTable {
  id: string;
  title: string;
  columns: string[];
  rows: AnalysisTableRow[];
}

export interface AnalysisOutcome {
  subject_id: string | number;
  propensity?: number | null;
  ate?: number | null;
  cate_group?: string | null;
  cate_value?: number | null;
  predicted_outcome?: number | null;
  iptw_weight?: number | null;
  hazard_ratio?: number | null;
  survival_prob?: number | null;
  shapley_values?: Record<string, number> | null;
  metadata?: Record<string, unknown>;
}

export interface CausalForestMetrics {
  mean_cate: number;
  cate_std: number;
  cate_range: [number, number];
  positive_response_rate: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface AnalysisMetadata {
  schema_version?: string;
  estimators?: string[];
  generated_at?: string;
  summary?: {
    n_subjects?: number;
    causal_forest?: CausalForestMetrics & { ate?: number };
    shapley?: {
      top_features?: FeatureImportance[];
    };
    iptw?: {
      mean_weight?: number;
      weight_range?: [number, number];
      effective_sample_size?: number;
    };
    cox_ph?: {
      hazard_ratio?: number;
      mean_survival_prob?: number;
    };
  };
}

export interface AnalysisRunResult {
  runId: string;
  templateId: string;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
  tables: AnalysisTable[];
  charts: AnalysisChart[];
  notes?: string;
  outcomes?: AnalysisOutcome[];
  metadata?: AnalysisMetadata;
}

export interface AnalysisRunProgress {
  runId: string;
  templateId: string;
  startedAt: string;
  progress: number;
  status: 'queued' | 'running' | 'completed' | 'cancelled' | 'error';
  errorMessage?: string;
}

export interface AnalysisState {
  templates: AnalysisTemplateMeta[];
  selectedTemplateId: string | null;
  activeRun: AnalysisRunProgress | null;
  history: AnalysisRunResult[];
  compareSelection: string[];
}

export interface SearchFilters {
  year: 'all' | number;
  source: SourceFilter;
}

export interface SearchState {
  query: string;
  filters: SearchFilters;
  selectedArticleIds: string[];
  excludedArticleIds: string[];
  currentPage: number;
  pageSize: number;
}

export interface ReportMethodsSection {
  schema: TrialSchema | null;
  narrative: string;
}

export interface ReportCohortSection {
  summary: CohortSummary | null;
  narrative: string;
  keyMetrics: Array<{ label: string; value: string }>;
}

export interface ReportResultsSection {
  analysis: AnalysisRunResult | null;
  narrative: string;
  keyFindings: string[];
}

export interface ReportData {
  title: string;
  authors: string[];
  abstract: string;
  methods: ReportMethodsSection;
  cohort: ReportCohortSection;
  results: ReportResultsSection;
  discussion: string;
  references: string[];
  createdAt: string;
}

export interface ReportState {
  draft: ReportData | null;
  lastGeneratedAt: string | null;
}

// Study Metadata
export interface StudyMetadata {
  id: string;
  name: string;
  purpose: string;
  nctId: string;
  medicine: string;
  createdAt: Date;
}

// Demo Mode Types
export interface DemoConfig {
  nctId: string;
  projectId: string;
  sampleSize: number;
  study?: StudyMetadata;
}

export interface DemoStageResult {
  status: 'bypassed' | 'executed';
  source: string;
  document_count?: number;
  inclusion_count?: number;
  exclusion_count?: number;
  feature_count?: number;
  total_subjects?: number;
  summary?: Record<string, unknown>;
  outcome_count?: number;
  metrics_summary?: Record<string, unknown>;
}

export interface DemoRunData {
  corpus: DemoStageResult;
  schema: DemoStageResult;
  cohort: DemoStageResult;
  analysis: DemoStageResult;
}

export interface FullModeFlowState {
  version?: number;
  currentStep: Step;
  steps: Record<Step, StepState>;
  search: SearchState;
  schema: TrialSchema | null;
  cohort: CohortState;
  analysis: AnalysisState;
  report: ReportState;
  mode: 'full';
}

export interface DemoModeFlowState {
  version?: number;
  currentStep: Step;
  steps: Record<Step, StepState>;
  search: SearchState;
  schema: TrialSchema | null;
  cohort: CohortState;
  analysis: AnalysisState;
  report: ReportState;
  mode: 'demo';
  demoConfig: DemoConfig;
  demoData?: DemoRunData;
  demoRunStatus: 'idle' | 'loading' | 'success' | 'error';
  demoRunError?: string;
}

export type FlowState = FullModeFlowState | DemoModeFlowState;

export type FlowAction =
  | {
      type: 'INIT_FROM_ROUTE';
      payload: { step: Step };
    }
  | {
      type: 'MARK_DONE';
      payload: { step: Step };
    }
  | {
      type: 'SET_IN_PROGRESS';
      payload: { step: Step };
    }
  | {
      type: 'MARK_ERROR';
      payload: { step: Step };
    }
  | {
      type: 'RESET_STEP';
      payload: { step: Step };
    }
  | {
      type: 'HYDRATE';
      payload: FlowState;
    }
  | {
      type: 'SEARCH_SET_QUERY';
      payload: { query: string };
    }
  | {
      type: 'SEARCH_SET_FILTERS';
      payload: { filters: Partial<SearchFilters> };
    }
  | {
      type: 'SEARCH_TOGGLE_SELECT';
      payload: { id: string };
    }
  | {
      type: 'SEARCH_TOGGLE_EXCLUDE';
      payload: { id: string };
    }
  | {
      type: 'SEARCH_CLEAR_SELECTIONS';
    }
  | {
      type: 'SEARCH_SET_PAGE';
      payload: { page: number };
    }
  | {
      type: 'SEARCH_SET_PAGE_SIZE';
      payload: { pageSize: number };
    }
  | {
      type: 'COHORT_SET_MAPPING';
      payload: { variableId: string; fieldId: string | null };
    }
  | {
      type: 'COHORT_RESET_MAPPING';
    }
  | {
      type: 'COHORT_SET_RESULT';
      payload: { result: CohortResult | null };
    }
  | {
      type: 'COHORT_SET_SIZE';
      payload: { size: number };
    }
  | {
      type: 'COHORT_SET_DATASET';
      payload: { datasetId: CohortDatasetId };
    }
  | {
      type: 'COHORT_SET_SEED';
      payload: { seed: string };
    }
  | {
      type: 'ANALYSIS_INIT_TEMPLATES';
      payload: { templates: AnalysisTemplateMeta[] };
    }
  | {
      type: 'ANALYSIS_SELECT_TEMPLATE';
      payload: { templateId: string | null };
    }
  | {
      type: 'ANALYSIS_START';
      payload: { run: AnalysisRunProgress };
    }
  | {
      type: 'ANALYSIS_UPDATE_PROGRESS';
      payload: { runId: string; progress: number };
    }
  | {
      type: 'ANALYSIS_COMPLETE';
      payload: { result: AnalysisRunResult };
    }
  | {
      type: 'ANALYSIS_FAIL';
      payload: { runId: string; error: string };
    }
  | {
      type: 'ANALYSIS_CANCEL';
      payload: { runId: string };
    }
  | {
      type: 'ANALYSIS_SET_COMPARE';
      payload: { runIds: string[] };
    }
  | {
      type: 'SCHEMA_SET_ACTIVE';
      payload: { schema: TrialSchema | null };
    }
  | {
      type: 'REPORT_SET_DRAFT';
      payload: { draft: ReportData | null };
    }
  | {
      type: 'SET_MODE';
      payload: { mode: 'full' | 'demo' };
    }
  | {
      type: 'SET_DEMO_CONFIG';
      payload: { config: DemoConfig };
    }
  | {
      type: 'DEMO_RUN_START';
    }
  | {
      type: 'DEMO_RUN_COMPLETE';
      payload: { result: DemoRunData };
    }
  | {
      type: 'DEMO_RUN_FAIL';
      payload: { error: string };
    }
  | {
      type: 'RESET_DEMO_STATE';
    };

export interface StepMeta {
  key: Step;
  name: string;
  description: string;
  href: string;
}
