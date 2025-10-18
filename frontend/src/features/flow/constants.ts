import type {
  AnalysisState,
  AnalysisTemplateMeta,
  CohortState,
  DemoConfig,
  FlowState,
  ReportState,
  SearchState,
  SourceFilter,
  Step,
  StepMeta,
  StepState,
} from './types';

export const STEPS: StepMeta[] = [
  {
    key: 'search',
    name: 'NCT Search',
    description:
      'Search clinical trials from ClinicalTrials.gov to begin trial design.',
    href: '/ct-search',
  },
  {
    key: 'schema',
    name: 'Schema Extraction',
    description:
      'Convert selected literature into structured trial schemas for downstream steps.',
    href: '/schema',
  },
  {
    key: 'cohort',
    name: 'Cohort Selection',
    description:
      'Apply schema criteria to datasets such as MIMIC to build patient cohorts.',
    href: '/cohort',
  },
  {
    key: 'analysis',
    name: 'Statistical Analysis',
    description:
      'Run statistical templates to evaluate outcomes and validate study design.',
    href: '/analysis',
  },
  {
    key: 'report',
    name: 'RWE Report',
    description:
      'Generate a publish-ready report with interactive visualisations.',
    href: '/report',
  },
];

export const STEP_ORDER: Step[] = STEPS.map((step) => step.key);

const DEFAULT_STEP_STATE: StepState = 'idle';

export const DEFAULT_SOURCE_FILTERS: SourceFilter[] = ['PubMed', 'CTgov'];

export const DEFAULT_SEARCH_STATE: SearchState = {
  query: '',
  filters: {
    year: 'all',
    source: 'all',
  },
  selectedArticleIds: [],
  excludedArticleIds: [],
  currentPage: 1,
  pageSize: 5,
};

export const DEFAULT_COHORT_STATE: CohortState = {
  mapping: {},
  cohortSize: 150,
  datasetId: 'mimic-iv',
  seed: 'trial-synth',
  result: null,
};

export const DEFAULT_DEMO_CONFIG: DemoConfig = {
  nctId: '',
  projectId: '',
  sampleSize: 100,
};

export const ANALYSIS_TEMPLATES: AnalysisTemplateMeta[] = [
  {
    id: 'propensity-score',
    name: 'Propensity Score Weighting',
    description:
      'Estimate propensity scores using logistic regression and weight cohorts to balance covariates.',
    inputs: ['treatmentFlag', 'covariates'],
    outputs: ['balanceTable', 'psDistribution'],
  },
  {
    id: 'hazard-ratio',
    name: 'Cox Hazard Ratio',
    description:
      'Run a Cox proportional hazards model to estimate hazard ratios with confidence intervals.',
    inputs: ['timeToEvent', 'eventIndicator', 'covariates'],
    outputs: ['hazardTable', 'survivalCurve'],
  },
  {
    id: 'outcome-diff',
    name: 'Outcome Difference-in-Means',
    description:
      'Compare treated vs control outcomes using bootstrap-adjusted difference-in-means.',
    inputs: ['outcomeMeasure', 'treatmentFlag'],
    outputs: ['summaryTable', 'effectBarChart'],
  },
];

export const DEFAULT_ANALYSIS_STATE: AnalysisState = {
  templates: ANALYSIS_TEMPLATES,
  selectedTemplateId: ANALYSIS_TEMPLATES[0]?.id ?? null,
  activeRun: null,
  history: [],
  compareSelection: [],
};

export const MAX_ANALYSIS_HISTORY = 10;

export const DEFAULT_REPORT_STATE: ReportState = {
  draft: null,
  lastGeneratedAt: null,
};

export const DEFAULT_FLOW_STATE: FlowState = {
  mode: 'full',
  currentStep: 'search',
  steps: STEP_ORDER.reduce<Record<Step, StepState>>((acc, step, index) => {
    acc[step] = index === 0 ? 'in-progress' : DEFAULT_STEP_STATE;
    return acc;
  }, {} as Record<Step, StepState>),
  search: DEFAULT_SEARCH_STATE,
  schema: null,
  cohort: DEFAULT_COHORT_STATE,
  analysis: DEFAULT_ANALYSIS_STATE,
  report: DEFAULT_REPORT_STATE,
};

export const FLOW_STORAGE_KEY = 'flowState';
