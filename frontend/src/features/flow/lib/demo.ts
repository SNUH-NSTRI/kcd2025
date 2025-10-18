import { ANALYSIS_TEMPLATES, DEFAULT_ANALYSIS_STATE, DEFAULT_SEARCH_STATE } from '../constants';
import type { FlowState } from '../types';
import { ARTICLES } from '@/features/search/lib/articles';
import { generateInitialSchema } from '@/features/schema/lib/generate-schema';
import { deepClone } from '@/features/schema/lib/utils';
import { generateCohort, suggestMappings } from '@/features/cohort/lib/generator';
import { synthesiseAnalysisResult } from '@/features/analysis/lib/synthesise';
import { buildReportData } from '@/features/report/lib/build-report';

function pickArticles(limit = 3) {
  return ARTICLES.slice(0, limit);
}

function buildDemoSearchState(selectedArticleIds: string[]): FlowState['search'] {
  return {
    ...DEFAULT_SEARCH_STATE,
    query: 'acute kidney injury multi-center',
    filters: { ...DEFAULT_SEARCH_STATE.filters },
    selectedArticleIds,
    excludedArticleIds: [],
    currentPage: 1,
    pageSize: DEFAULT_SEARCH_STATE.pageSize,
  };
}

/**
 * Create demo flow state with pre-computed fixture data
 * Uses lightweight summaries from fixture JSON instead of loading full datasets
 */
export function createDemoFlowState(): FlowState {
  const articles = pickArticles();
  const selectedArticleIds = articles.map((article) => article.id);

  const schema = deepClone(generateInitialSchema(articles));
  const suggestions = suggestMappings(schema.variables);
  const mapping = schema.variables.reduce<Record<string, string | null>>((acc, variable) => {
    acc[variable.id] = suggestions[variable.id] ?? null;
    return acc;
  }, {});

  // Demo configuration
  const demoNctId = 'NCT03389555';

  // Generate lightweight synthetic cohort for demo
  const cohortResult = generateCohort({
    datasetId: 'mimic-iv',
    size: 11858,
    seed: `demo-${demoNctId}`,
  });

  const template = ANALYSIS_TEMPLATES.find((item) => item.id === 'hazard-ratio') ?? ANALYSIS_TEMPLATES[0];
  const runId = `demo-run-${Math.random().toString(36).slice(2, 8)}`;
  const startedAt = new Date(Date.now() - 5 * 60 * 1000).toISOString();
  const analysisResult = synthesiseAnalysisResult(template, cohortResult, runId, startedAt);

  const reportDraft = buildReportData({
    selectedArticleIds,
    cohort: cohortResult,
    analysisRuns: [analysisResult],
    schema,
  });

  return {
    mode: 'demo',
    currentStep: 'report',
    steps: {
      search: 'done',
      schema: 'done',
      cohort: 'done',
      analysis: 'done',
      report: 'done',
    },
    search: buildDemoSearchState(selectedArticleIds),
    schema,
    cohort: {
      mapping,
      cohortSize: cohortResult.summary.size,
      datasetId: cohortResult.summary.datasetId,
      seed: cohortResult.seed,
      result: cohortResult,
    },
    analysis: {
      templates: [...DEFAULT_ANALYSIS_STATE.templates],
      selectedTemplateId: template?.id ?? null,
      activeRun: null,
      history: [analysisResult],
      compareSelection: [],
    },
    report: {
      draft: reportDraft,
      lastGeneratedAt: reportDraft.createdAt,
    },
    demoConfig: {
      nctId: demoNctId,
      projectId: 'demo_project_001',
      sampleSize: cohortResult.summary.size,
      study: {
        title: 'Adjunctive Glucocorticoid Therapy in Patients with Septic Shock',
        nctId: demoNctId,
        phase: 'Phase 3',
        medicine: 'hydrocortisonenasucc',
      },
    },
    demoRunStatus: 'success',
  } satisfies FlowState;
}
