'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  DEFAULT_ANALYSIS_STATE,
  DEFAULT_COHORT_STATE,
  DEFAULT_DEMO_CONFIG,
  DEFAULT_FLOW_STATE,
  DEFAULT_REPORT_STATE,
  DEFAULT_SEARCH_STATE,
  FLOW_STORAGE_KEY,
  MAX_ANALYSIS_HISTORY,
  STEP_ORDER,
  STEPS,
} from './constants';
import { useAudit } from '@/features/audit';
import type {
  AnalysisRunProgress,
  AnalysisRunResult,
  AnalysisState,
  CohortDatasetId,
  CohortResult,
  CohortState,
  DemoConfig,
  DemoRunData,
  FlowAction,
  FlowState,
  FullModeFlowState,
  ReportData,
  ReportState,
  SearchFilters,
  SearchState,
  Step,
  StepState,
  StudyMetadata,
} from './types';
import type { TrialSchema } from '@/features/schema/types';
import { deepClone } from '@/features/schema/lib/utils';
import { createDemoFlowState } from './lib/demo';

function uniqueIds(ids: string[]): string[] {
  return Array.from(new Set(ids));
}

function mergeSearchState(search: Partial<SearchState> | undefined): SearchState {
  const safeSearch = search ?? DEFAULT_SEARCH_STATE;
  const filters: SearchFilters = {
    ...DEFAULT_SEARCH_STATE.filters,
    ...(safeSearch.filters ?? {}),
  };

  const selected = uniqueIds(safeSearch.selectedArticleIds ?? []);
  const excluded = uniqueIds(
    (safeSearch.excludedArticleIds ?? []).filter((id) => !selected.includes(id)),
  );

  return {
    ...DEFAULT_SEARCH_STATE,
    ...safeSearch,
    filters,
    selectedArticleIds: selected,
    excludedArticleIds: excluded,
    currentPage:
      typeof safeSearch.currentPage === 'number' && safeSearch.currentPage > 0
        ? safeSearch.currentPage
        : DEFAULT_SEARCH_STATE.currentPage,
    pageSize:
      typeof safeSearch.pageSize === 'number' && safeSearch.pageSize > 0
        ? safeSearch.pageSize
        : DEFAULT_SEARCH_STATE.pageSize,
  };
}

function isValidDatasetId(value: unknown): value is CohortDatasetId {
  return value === 'mimic-iv' || value === 'k-mimic' || value === 'demo';
}

function mergeCohortState(cohort: Partial<CohortState> | undefined): CohortState {
  const base: CohortState = {
    ...DEFAULT_COHORT_STATE,
    mapping: { ...DEFAULT_COHORT_STATE.mapping },
  };

  if (!cohort) {
    return base;
  }

  const mappingEntries = cohort.mapping
    ? Object.entries(cohort.mapping).reduce<Record<string, string | null>>(
        (acc, [key, value]) => {
          acc[key] = value ?? null;
          return acc;
        },
        {},
      )
    : {};

  return {
    mapping: mappingEntries,
    cohortSize:
      typeof cohort.cohortSize === 'number' && cohort.cohortSize > 0
        ? Math.floor(cohort.cohortSize)
        : base.cohortSize,
    datasetId: isValidDatasetId(cohort.datasetId)
      ? cohort.datasetId
      : base.datasetId,
    seed: typeof cohort.seed === 'string' && cohort.seed.trim().length > 0
      ? cohort.seed
      : base.seed,
    result: cohort.result ?? null,
  };
}

function mergeAnalysisState(analysis: Partial<AnalysisState> | undefined): AnalysisState {
  const base: AnalysisState = {
    ...DEFAULT_ANALYSIS_STATE,
    templates: [...DEFAULT_ANALYSIS_STATE.templates],
    history: [...DEFAULT_ANALYSIS_STATE.history],
    compareSelection: [...DEFAULT_ANALYSIS_STATE.compareSelection],
  };

  if (!analysis) {
    return base;
  }

  const history = analysis.history ?? base.history;
  const compareSelection = analysis.compareSelection ?? base.compareSelection;

  return {
    templates: base.templates,
    selectedTemplateId:
      analysis.selectedTemplateId &&
      base.templates.some((template) => template.id === analysis.selectedTemplateId)
        ? analysis.selectedTemplateId
        : base.selectedTemplateId,
    activeRun: analysis.activeRun ?? null,
    history,
    compareSelection,
  };
}

function mergeReportState(report: Partial<ReportState> | undefined): ReportState {
  const base: ReportState = { ...DEFAULT_REPORT_STATE };
  if (!report) {
    return base;
  }

  const draft = report.draft ?? null;
  const lastGeneratedAt =
    typeof report.lastGeneratedAt === 'string'
      ? report.lastGeneratedAt
      : draft?.createdAt ?? base.lastGeneratedAt;

  return {
    draft,
    lastGeneratedAt: lastGeneratedAt ?? null,
  };
}

function mergeSchemaState(schema: TrialSchema | null | undefined): TrialSchema | null {
  if (!schema) {
    return null;
  }
  return deepClone(schema);
}

const CURRENT_STATE_VERSION = 1;

/**
 * Migrates FlowState from older versions to current version.
 * Fixes corrupted state where multiple steps are marked as 'in-progress'.
 */
function migrateFlowState(state: Partial<FlowState>): Partial<FlowState> {
  // If no version or old version, apply migrations
  if (!state.version || state.version < CURRENT_STATE_VERSION) {
    const migratedState = { ...state };

    // Fix multi-progress bug: only one step should be 'in-progress' at a time
    if (state.steps) {
      const inProgressSteps = Object.entries(state.steps)
        .filter(([_, status]) => status === 'in-progress')
        .map(([key]) => key);

      // If multiple steps are in-progress, reset all to idle except the first one (search)
      if (inProgressSteps.length > 1) {
        const newSteps = { ...state.steps };
        inProgressSteps.forEach((stepKey) => {
          if (stepKey !== 'search') {
            newSteps[stepKey as Step] = 'idle';
          }
        });
        migratedState.steps = newSteps;
      }
    }

    migratedState.version = CURRENT_STATE_VERSION;
    return migratedState;
  }

  return state;
}

function ensureStateDefaults(state: Partial<FlowState>): FlowState {
  const steps: Record<Step, StepState> = {} as Record<Step, StepState>;
  STEP_ORDER.forEach((step, index) => {
    if (state.steps && state.steps[step]) {
      steps[step] = state.steps[step];
    } else {
      steps[step] = index === 0 ? 'in-progress' : 'idle';
    }
  });

  const currentStep =
    state.currentStep && steps[state.currentStep]
      ? state.currentStep
      : STEP_ORDER[0];

  const commonState = {
    version: CURRENT_STATE_VERSION,
    currentStep,
    steps,
    search: mergeSearchState(state.search),
    schema: mergeSchemaState(state.schema),
    cohort: mergeCohortState(state.cohort),
    analysis: mergeAnalysisState(state.analysis),
    report: mergeReportState(state.report),
  };

  if (state.mode === 'demo') {
    const demoConfig: DemoConfig = state.demoConfig ?? DEFAULT_DEMO_CONFIG;
    return {
      ...commonState,
      mode: 'demo',
      demoConfig,
      demoData: state.demoData ?? undefined,
      demoRunStatus: state.demoRunStatus ?? 'idle',
      demoRunError: state.demoRunError ?? undefined,
    };
  }

  return {
    ...commonState,
    mode: 'full',
  };
}

function flowReducer(state: FlowState, action: FlowAction): FlowState {
  switch (action.type) {
    case 'HYDRATE': {
      const migrated = migrateFlowState(action.payload);
      return ensureStateDefaults(migrated);
    }
    case 'INIT_FROM_ROUTE': {
      const step = action.payload.step;
      if (!STEP_ORDER.includes(step)) {
        return state;
      }

      // Only update currentStep, don't change step states
      // Step states should only change when user explicitly starts/completes work
      return {
        ...state,
        currentStep: step,
      };
    }
    case 'SET_IN_PROGRESS': {
      const step = action.payload.step;
      const nextSteps = { ...state.steps, [step]: 'in-progress' };
      return {
        ...state,
        currentStep: step,
        steps: nextSteps,
      };
    }
    case 'MARK_DONE': {
      const step = action.payload.step;
      const nextSteps = { ...state.steps, [step]: 'done' };

      // Don't automatically set next step to 'in-progress'
      // User should explicitly start the next step
      return {
        ...state,
        steps: nextSteps,
      };
    }
    case 'MARK_ERROR': {
      const step = action.payload.step;
      const nextSteps = { ...state.steps, [step]: 'error' };
      return {
        ...state,
        currentStep: step,
        steps: nextSteps,
      };
    }
    case 'RESET_STEP': {
      const step = action.payload.step;
      const nextSteps = { ...state.steps, [step]: 'idle' };
      return {
        ...state,
        currentStep: state.currentStep,
        steps: nextSteps,
      };
    }
    case 'SEARCH_SET_QUERY': {
      return {
        ...state,
        search: {
          ...state.search,
          query: action.payload.query,
          currentPage: 1,
        },
      };
    }
    case 'SEARCH_SET_FILTERS': {
      return {
        ...state,
        search: {
          ...state.search,
          filters: {
            ...state.search.filters,
            ...action.payload.filters,
          },
          currentPage: 1,
        },
      };
    }
    case 'SEARCH_TOGGLE_SELECT': {
      const id = action.payload.id;
      const selected = new Set(state.search.selectedArticleIds);
      const excluded = new Set(state.search.excludedArticleIds);
      if (selected.has(id)) {
        selected.delete(id);
      } else {
        selected.add(id);
        excluded.delete(id);
      }

      return {
        ...state,
        search: {
          ...state.search,
          selectedArticleIds: Array.from(selected),
          excludedArticleIds: Array.from(excluded),
        },
      };
    }
    case 'SEARCH_TOGGLE_EXCLUDE': {
      const id = action.payload.id;
      const selected = new Set(state.search.selectedArticleIds);
      const excluded = new Set(state.search.excludedArticleIds);
      if (excluded.has(id)) {
        excluded.delete(id);
      } else {
        excluded.add(id);
        selected.delete(id);
      }

      return {
        ...state,
        search: {
          ...state.search,
          selectedArticleIds: Array.from(selected),
          excludedArticleIds: Array.from(excluded),
        },
      };
    }
    case 'SEARCH_CLEAR_SELECTIONS': {
      return {
        ...state,
        search: {
          ...state.search,
          selectedArticleIds: [],
          excludedArticleIds: [],
        },
      };
    }
    case 'SEARCH_SET_PAGE': {
      return {
        ...state,
        search: {
          ...state.search,
          currentPage: Math.max(1, action.payload.page),
        },
      };
    }
    case 'SEARCH_SET_PAGE_SIZE': {
      return {
        ...state,
        search: {
          ...state.search,
          pageSize: Math.max(1, action.payload.pageSize),
          currentPage: 1,
        },
      };
    }
    case 'COHORT_SET_MAPPING': {
      const { variableId, fieldId } = action.payload;
      const nextMapping = { ...state.cohort.mapping };
      if (fieldId === null) {
        nextMapping[variableId] = null;
      } else {
        nextMapping[variableId] = fieldId;
      }
      return {
        ...state,
        cohort: {
          ...state.cohort,
          mapping: nextMapping,
          result: null,
        },
      };
    }
    case 'COHORT_RESET_MAPPING': {
      return {
        ...state,
        cohort: {
          ...state.cohort,
          mapping: {},
          result: null,
        },
      };
    }
    case 'COHORT_SET_RESULT': {
      return {
        ...state,
        cohort: {
          ...state.cohort,
          result: action.payload.result,
        },
      };
    }
    case 'COHORT_SET_SIZE': {
      return {
        ...state,
        cohort: {
          ...state.cohort,
          cohortSize: Math.max(10, action.payload.size),
          result: null,
        },
      };
    }
    case 'COHORT_SET_DATASET': {
      return {
        ...state,
        cohort: {
          ...state.cohort,
          datasetId: action.payload.datasetId,
          result: null,
        },
      };
    }
    case 'COHORT_SET_SEED': {
      return {
        ...state,
        cohort: {
          ...state.cohort,
          seed: action.payload.seed,
          result: null,
        },
      };
    }
    case 'ANALYSIS_INIT_TEMPLATES': {
      const templates = action.payload.templates;
      const selectedTemplateId = templates.some(
        (template) => template.id === state.analysis.selectedTemplateId,
      )
        ? state.analysis.selectedTemplateId
        : templates[0]?.id ?? null;
      return {
        ...state,
        analysis: {
          ...state.analysis,
          templates,
          selectedTemplateId,
        },
      };
    }
    case 'ANALYSIS_SELECT_TEMPLATE': {
      return {
        ...state,
        analysis: {
          ...state.analysis,
          selectedTemplateId: action.payload.templateId,
        },
      };
    }
    case 'ANALYSIS_START': {
      return {
        ...state,
        analysis: {
          ...state.analysis,
          activeRun: action.payload.run,
        },
      };
    }
    case 'ANALYSIS_UPDATE_PROGRESS': {
      if (!state.analysis.activeRun || state.analysis.activeRun.runId !== action.payload.runId) {
        return state;
      }
      return {
        ...state,
        analysis: {
          ...state.analysis,
          activeRun: {
            ...state.analysis.activeRun,
            progress: action.payload.progress,
            status: action.payload.progress >= 100 ? 'completed' : 'running',
          },
        },
      };
    }
    case 'ANALYSIS_COMPLETE': {
      const filteredHistory = state.analysis.history
        .filter((run) => run.runId !== action.payload.result.runId)
        .concat(action.payload.result);
      const trimmedHistory = filteredHistory.slice(-MAX_ANALYSIS_HISTORY);
      const validRunIds = new Set(trimmedHistory.map((run) => run.runId));

      return {
        ...state,
        analysis: {
          ...state.analysis,
          activeRun: null,
          history: trimmedHistory,
          compareSelection: state.analysis.compareSelection.filter((id) => validRunIds.has(id)),
        },
      };
    }
    case 'ANALYSIS_FAIL': {
      if (!state.analysis.activeRun || state.analysis.activeRun.runId !== action.payload.runId) {
        return state;
      }
      return {
        ...state,
        analysis: {
          ...state.analysis,
          activeRun: null,
        },
      };
    }
    case 'ANALYSIS_CANCEL': {
      if (!state.analysis.activeRun || state.analysis.activeRun.runId !== action.payload.runId) {
        return state;
      }
      return {
        ...state,
        analysis: {
          ...state.analysis,
          activeRun: null,
        },
      };
    }
    case 'ANALYSIS_SET_COMPARE': {
      return {
        ...state,
        analysis: {
          ...state.analysis,
          compareSelection: action.payload.runIds,
        },
      };
    }
    case 'REPORT_SET_DRAFT': {
      const draft = action.payload.draft;
      return {
        ...state,
        report: {
          draft,
          lastGeneratedAt: draft?.createdAt ?? state.report.lastGeneratedAt ?? null,
        },
      };
    }
    case 'SCHEMA_SET_ACTIVE': {
      return {
        ...state,
        schema: mergeSchemaState(action.payload.schema),
      };
    }

    case 'SET_MODE': {
      if (state.mode === action.payload.mode) {
        return state; // No change if mode is already set
      }

      const {
        currentStep,
        steps,
        search,
        schema,
        cohort,
        analysis,
        report,
      } = state;

      const commonState = {
        currentStep,
        steps,
        search,
        schema,
        cohort,
        analysis,
        report,
      };

      if (action.payload.mode === 'demo') {
        return {
          ...commonState,
          mode: 'demo',
          demoConfig: DEFAULT_DEMO_CONFIG,
          demoRunStatus: 'idle',
          demoData: undefined,
          demoRunError: undefined,
        };
      }

      // Transitioning to 'full' mode
      return {
        ...commonState,
        mode: 'full',
      };
    }

    case 'SET_DEMO_CONFIG': {
      if (state.mode !== 'demo') {
        return state; // Action is only valid in demo mode
      }
      return {
        ...state,
        demoConfig: action.payload.config,
      };
    }

    case 'DEMO_RUN_START': {
      if (state.mode !== 'demo') {
        return state;
      }
      return {
        ...state,
        demoRunStatus: 'loading',
        demoRunError: undefined,
      };
    }

    case 'DEMO_RUN_COMPLETE': {
      if (state.mode !== 'demo') {
        return state;
      }
      return {
        ...state,
        demoRunStatus: 'success',
        demoData: action.payload.result,
        demoRunError: undefined,
      };
    }

    case 'DEMO_RUN_FAIL': {
      if (state.mode !== 'demo') {
        return state;
      }
      return {
        ...state,
        demoRunStatus: 'error',
        demoRunError: action.payload.error,
      };
    }

    case 'RESET_DEMO_STATE': {
      if (state.mode !== 'demo') {
        return state;
      }
      // This action exits demo mode entirely and resets the application
      // to the default state for the standard 'full' workflow.
      return { ...DEFAULT_FLOW_STATE };
    }

    default:
      return state;
  }
}

interface FlowContextValue {
  state: FlowState;
  setInProgress: (step: Step) => void;
  markDone: (step: Step) => void;
  markError: (step: Step) => void;
  resetStep: (step: Step) => void;
  setSearchQuery: (query: string) => void;
  setSearchFilters: (filters: Partial<SearchFilters>) => void;
  toggleArticleSelection: (id: string) => void;
  toggleArticleExclusion: (id: string) => void;
  clearSearchSelections: () => void;
  setSearchPage: (page: number) => void;
  setSearchPageSize: (pageSize: number) => void;
  setCohortMapping: (variableId: string, fieldId: string | null) => void;
  resetCohort: () => void;
  setCohortResult: (result: CohortResult | null) => void;
  setCohortSize: (size: number) => void;
  setCohortDataset: (datasetId: CohortDatasetId) => void;
  setCohortSeed: (seed: string) => void;
  selectAnalysisTemplate: (templateId: string | null) => void;
  startAnalysisRun: (run: AnalysisRunProgress) => void;
  updateAnalysisProgress: (runId: string, progress: number) => void;
  completeAnalysisRun: (result: AnalysisRunResult) => void;
  failAnalysisRun: (runId: string, error: string) => void;
  cancelAnalysisRun: (runId: string) => void;
  setAnalysisCompareSelection: (runIds: string[]) => void;
  setReportDraft: (draft: ReportData | null) => void;
  setSchemaDraft: (schema: TrialSchema | null) => void;
  canAccessStep: (step: Step) => boolean;
  resetFlow: () => void;
  // Demo mode methods
  activatePrebuiltDemo: () => void;
  exitDemoMode: () => void;
  runDemoPipeline: () => Promise<void>;
  setMode: (mode: 'full' | 'demo') => void;
  setDemoConfig: (config: DemoConfig) => void;
  // Study creation
  createNewStudy: (data: { name: string; purpose: string; nctId: string; medicine: string }) => void;
}

const FlowContext = createContext<FlowContextValue | undefined>(undefined);

function parseStoredState(raw: string | null): FlowState | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<FlowState>;
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    return ensureStateDefaults(parsed);
  } catch (error) {
    console.error('Failed to parse stored flow state', error);
    return null;
  }
}

const ROUTE_TO_STEP = STEPS.reduce<Record<string, Step>>((acc, step) => {
  acc[step.href] = step.key;
  return acc;
}, {});

export function FlowProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);
  const ignoredInitialRoute = useRef(false);
  const [state, dispatch] = useReducer(flowReducer, DEFAULT_FLOW_STATE);
  const { createEvent } = useAudit();

  useEffect(() => {
    const stored = parseStoredState(
      typeof window === 'undefined'
        ? null
        : window.localStorage.getItem(FLOW_STORAGE_KEY),
    );

    if (stored) {
      dispatch({ type: 'HYDRATE', payload: stored });
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(FLOW_STORAGE_KEY, JSON.stringify(state));
  }, [hydrated, state]);

  useEffect(() => {
    if (!pathname) return;
    if (!hydrated && !ignoredInitialRoute.current) {
      ignoredInitialRoute.current = true;
      return;
    }

    // Update currentStep based on route, but don't change step states
    // Step states should only change when user explicitly starts/completes work
    const step = ROUTE_TO_STEP[pathname];
    if (step) {
      dispatch({ type: 'INIT_FROM_ROUTE', payload: { step } });
    }
  }, [hydrated, pathname]);

  const setInProgress = useCallback(
    (step: Step) => {
      const previous = state.steps[step];
      dispatch({ type: 'SET_IN_PROGRESS', payload: { step } });
      if (previous !== 'in-progress') {
        createEvent('flow.step.started', 'flow', {
          summary: `Marked ${step} step as in progress.`,
          step,
          previousStatus: previous,
        });
      }
    },
    [createEvent, state.steps],
  );
  const markDone = useCallback(
    (step: Step) => {
      const previous = state.steps[step];
      dispatch({ type: 'MARK_DONE', payload: { step } });
      if (previous !== 'done') {
        createEvent('flow.step.completed', 'flow', {
          summary: `Completed ${step} step.`,
          step,
          previousStatus: previous,
        });
      }
    },
    [createEvent, state.steps],
  );
  const markError = useCallback(
    (step: Step) => {
      dispatch({ type: 'MARK_ERROR', payload: { step } });
      createEvent('flow.step.error', 'flow', {
        summary: `Flagged ${step} step with an error state.`,
        step,
      });
    },
    [createEvent],
  );
  const resetStep = useCallback(
    (step: Step) => {
      const previous = state.steps[step];
      dispatch({ type: 'RESET_STEP', payload: { step } });
      createEvent('flow.step.reset', 'flow', {
        summary: `Reset ${step} step to idle.`,
        step,
        previousStatus: previous,
      });
    },
    [createEvent, state.steps],
  );
  const canAccessStep = useCallback(
    (step: Step) => {
      if (step === state.currentStep) {
        return true;
      }
      if (step === 'search') {
        return true;
      }
      const index = STEP_ORDER.indexOf(step);
      if (index <= 0) {
        return true;
      }
      const prerequisite = STEP_ORDER[index - 1];
      return state.steps[prerequisite] === 'done';
    },
    [state.currentStep, state.steps],
  );
  const resetFlow = useCallback(() => {
    console.log('🔄 Executing UPDATED resetFlow - redirecting to /dashboard');
    if (typeof window !== 'undefined') {
      window.localStorage.clear();
    }
    dispatch({ type: 'HYDRATE', payload: DEFAULT_FLOW_STATE });
    console.log('📍 About to push to /dashboard');
    router.push('/dashboard');
    createEvent('flow.reset', 'flow', {
      summary: 'Workflow state reset to dashboard.',
    });
  }, [createEvent, router]);
  const activatePrebuiltDemo = useCallback(() => {
    const demoState = createDemoFlowState();
    dispatch({ type: 'HYDRATE', payload: demoState });
    router.push('/report');
    createEvent('flow.demo.activated', 'flow', {
      summary: 'Activated pre-built demo pipeline with lightweight fixture data.',
    });
  }, [createEvent, router]);
  const exitDemoMode = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(FLOW_STORAGE_KEY);
    }
    dispatch({ type: 'RESET_DEMO_STATE' });
    router.push('/dashboard');
    createEvent('flow.demo.exited', 'flow', {
      summary: 'Exited demo mode and returned to dashboard.',
    });
  }, [createEvent, router]);
  const runDemoPipeline = useCallback(async () => {
    if (state.mode !== 'demo') return;

    dispatch({ type: 'DEMO_RUN_START' });
    createEvent('flow.demo.run.started', 'flow', {
      summary: 'Demo pipeline run started.',
      config: state.demoConfig,
    });

    try {
      // Simulate API call to the backend
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // This is where the actual API call would go, e.g.:
      // const result = await api.runDemo(state.demoConfig);

      // Mocked result for now
      const result: DemoRunData = {
        corpus: { status: 'executed', source: 'mock', document_count: 1 },
        schema: { status: 'executed', source: 'mock', feature_count: 25 },
        cohort: { status: 'executed', source: 'mock', total_subjects: 100 },
        analysis: { status: 'executed', source: 'mock', outcome_count: 3 },
      };

      dispatch({ type: 'DEMO_RUN_COMPLETE', payload: { result } });
      createEvent('flow.demo.run.completed', 'flow', {
        summary: 'Demo pipeline run completed successfully.',
      });
    } catch (err) {
      const error = err instanceof Error ? err.message : 'An unknown error occurred.';
      dispatch({ type: 'DEMO_RUN_FAIL', payload: { error } });
      createEvent('flow.demo.run.failed', 'flow', {
        summary: 'Demo pipeline run failed.',
        error,
      });
    }
  }, [createEvent, state]);
  const setMode = useCallback(
    (mode: 'full' | 'demo') => dispatch({ type: 'SET_MODE', payload: { mode } }),
    [],
  );
  const setDemoConfig = useCallback(
    (config: DemoConfig) =>
      dispatch({ type: 'SET_DEMO_CONFIG', payload: { config } }),
    [],
  );
  const createNewStudy = useCallback(
    (data: { name: string; purpose: string; nctId: string; medicine: string }) => {
      const study: StudyMetadata = {
        id: `study_${Date.now()}`,
        name: data.name,
        purpose: data.purpose,
        nctId: data.nctId,
        medicine: data.medicine,
        createdAt: new Date(),
      };

      // Set to demo mode with study metadata
      dispatch({ type: 'SET_MODE', payload: { mode: 'demo' } });
      dispatch({
        type: 'SET_DEMO_CONFIG',
        payload: {
          config: {
            nctId: data.nctId,
            projectId: `project_${Date.now()}`,
            sampleSize: 100,
            study,
          },
        },
      });

      // Mark NCT Search step as done when study is created
      dispatch({ type: 'MARK_DONE', payload: { step: 'search' } });

      createEvent('flow.study.created', 'flow', {
        summary: `Created new study: ${data.name} with medicine: ${data.medicine}`,
        studyId: study.id,
        nctId: data.nctId,
        medicine: data.medicine,
      });
    },
    [createEvent],
  );
  const setSearchQuery = useCallback(
    (query: string) => dispatch({ type: 'SEARCH_SET_QUERY', payload: { query } }),
    [],
  );
  const setSearchFilters = useCallback(
    (filters: Partial<SearchFilters>) =>
      dispatch({ type: 'SEARCH_SET_FILTERS', payload: { filters } }),
    [],
  );
  const toggleArticleSelection = useCallback(
    (id: string) => dispatch({ type: 'SEARCH_TOGGLE_SELECT', payload: { id } }),
    [],
  );
  const toggleArticleExclusion = useCallback(
    (id: string) => dispatch({ type: 'SEARCH_TOGGLE_EXCLUDE', payload: { id } }),
    [],
  );
  const clearSearchSelections = useCallback(
    () => dispatch({ type: 'SEARCH_CLEAR_SELECTIONS' }),
    [],
  );
  const setSearchPage = useCallback(
    (page: number) => dispatch({ type: 'SEARCH_SET_PAGE', payload: { page } }),
    [],
  );
  const setSearchPageSize = useCallback(
    (pageSize: number) =>
      dispatch({ type: 'SEARCH_SET_PAGE_SIZE', payload: { pageSize } }),
    [],
  );
  const setCohortMapping = useCallback(
    (variableId: string, fieldId: string | null) =>
      dispatch({ type: 'COHORT_SET_MAPPING', payload: { variableId, fieldId } }),
    [],
  );
  const resetCohort = useCallback(
    () => dispatch({ type: 'COHORT_RESET_MAPPING' }),
    [],
  );
  const setCohortResult = useCallback(
    (result: CohortResult | null) =>
      dispatch({ type: 'COHORT_SET_RESULT', payload: { result } }),
    [],
  );
  const setCohortSize = useCallback(
    (size: number) => dispatch({ type: 'COHORT_SET_SIZE', payload: { size } }),
    [],
  );
  const setCohortDataset = useCallback(
    (datasetId: CohortDatasetId) =>
      dispatch({ type: 'COHORT_SET_DATASET', payload: { datasetId } }),
    [],
  );
  const setCohortSeed = useCallback(
    (seed: string) => dispatch({ type: 'COHORT_SET_SEED', payload: { seed } }),
    [],
  );
  const selectAnalysisTemplate = useCallback(
    (templateId: string | null) =>
      dispatch({ type: 'ANALYSIS_SELECT_TEMPLATE', payload: { templateId } }),
    [],
  );
  const startAnalysisRun = useCallback(
    (run: AnalysisRunProgress) =>
      dispatch({ type: 'ANALYSIS_START', payload: { run } }),
    [],
  );
  const updateAnalysisProgress = useCallback(
    (runId: string, progress: number) =>
      dispatch({ type: 'ANALYSIS_UPDATE_PROGRESS', payload: { runId, progress } }),
    [],
  );
  const completeAnalysisRun = useCallback(
    (result: AnalysisRunResult) =>
      dispatch({ type: 'ANALYSIS_COMPLETE', payload: { result } }),
    [],
  );
  const failAnalysisRun = useCallback(
    (runId: string, error: string) =>
      dispatch({ type: 'ANALYSIS_FAIL', payload: { runId, error } }),
    [],
  );
  const cancelAnalysisRun = useCallback(
    (runId: string) => dispatch({ type: 'ANALYSIS_CANCEL', payload: { runId } }),
    [],
  );
  const setAnalysisCompareSelection = useCallback(
    (runIds: string[]) =>
      dispatch({ type: 'ANALYSIS_SET_COMPARE', payload: { runIds } }),
    [],
  );
  const setReportDraft = useCallback(
    (draft: ReportData | null) =>
      dispatch({ type: 'REPORT_SET_DRAFT', payload: { draft } }),
    [],
  );
  const setSchemaDraft = useCallback(
    (schema: TrialSchema | null) =>
      dispatch({ type: 'SCHEMA_SET_ACTIVE', payload: { schema } }),
    [],
  );

  const value = useMemo<FlowContextValue>(
    () => ({
      state,
      setInProgress,
      markDone,
      markError,
      resetStep,
      setSearchQuery,
      setSearchFilters,
      toggleArticleSelection,
      toggleArticleExclusion,
      clearSearchSelections,
      setSearchPage,
      setSearchPageSize,
      setCohortMapping,
      resetCohort,
      setCohortResult,
      setCohortSize,
      setCohortDataset,
      setCohortSeed,
      selectAnalysisTemplate,
      startAnalysisRun,
      updateAnalysisProgress,
      completeAnalysisRun,
      failAnalysisRun,
      cancelAnalysisRun,
      setAnalysisCompareSelection,
      setReportDraft,
      setSchemaDraft,
      canAccessStep,
      resetFlow,
      activatePrebuiltDemo,
      exitDemoMode,
      runDemoPipeline,
      setMode,
      setDemoConfig,
      createNewStudy,
    }),
    [
      clearSearchSelections,
      createNewStudy,
      markDone,
      markError,
      resetStep,
      setInProgress,
      setSearchFilters,
      setSearchPage,
      setSearchPageSize,
      setSearchQuery,
      state,
      toggleArticleExclusion,
      toggleArticleSelection,
      resetCohort,
      setCohortDataset,
      setCohortMapping,
      setCohortResult,
      setCohortSeed,
      setCohortSize,
      cancelAnalysisRun,
      completeAnalysisRun,
      failAnalysisRun,
      setReportDraft,
      selectAnalysisTemplate,
      setAnalysisCompareSelection,
      startAnalysisRun,
      updateAnalysisProgress,
      setSchemaDraft,
      canAccessStep,
      resetFlow,
      activatePrebuiltDemo,
      exitDemoMode,
      runDemoPipeline,
      setMode,
      setDemoConfig,
    ],
  );

  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>;
}

export function useFlow() {
  const ctx = useContext(FlowContext);
  if (!ctx) {
    throw new Error('useFlow must be used within FlowProvider');
  }
  return ctx;
}

export function useStepState(step: Step): StepState {
  const {
    state: { steps },
  } = useFlow();
  return steps[step];
}

export function useSearchState(): SearchState {
  const {
    state: { search },
  } = useFlow();
  return search;
}

export function useCohortState(): CohortState {
  const {
    state: { cohort },
  } = useFlow();
  return cohort;
}

export function useAnalysisState(): AnalysisState {
  const {
    state: { analysis },
  } = useFlow();
  return analysis;
}
