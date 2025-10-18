import { ARTICLES } from '@/features/search/lib/articles';
import type { Article } from '@/features/search/types';
import { getSchemaStorageKey } from '@/features/schema/constants';
import { loadStoredVersions } from '@/features/schema/lib/versioning';
import { deepClone } from '@/features/schema/lib/utils';
import type {
  AnalysisRunResult,
  CohortResult,
  ReportCohortSection,
  ReportData,
  ReportMethodsSection,
  ReportResultsSection,
} from '@/features/flow/types';
import type { TrialSchema } from '@/features/schema/types';

const DATASET_LABELS: Record<string, string> = {
  'mimic-iv': 'MIMIC-IV',
  'k-mimic': 'K-MIMIC',
  demo: 'Demo dataset',
};

function formatDatasetLabel(datasetId: string | undefined): string {
  if (!datasetId) {
    return 'unspecified dataset';
  }
  return DATASET_LABELS[datasetId] ?? datasetId;
}

function toPercent(value: number | null, fractionDigits = 1): string {
  if (value === null || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

function coerceNumber(value: unknown): number | null {
  if (typeof value === 'number') return value;
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function extractPrimaryAnalysis(analysisRuns: AnalysisRunResult[]): AnalysisRunResult | null {
  if (analysisRuns.length === 0) {
    return null;
  }
  return analysisRuns[analysisRuns.length - 1];
}

function formatKeyFinding(label: string, value: string): string {
  return `${label}: ${value}`;
}

function buildMethodsSection(schema: TrialSchema | null): ReportMethodsSection {
  if (!schema) {
    return {
      schema: null,
      narrative:
        'Schema extraction is pending. Once the schema workspace is committed, the protocol summary will populate this section automatically.',
    };
  }

  const inclusionCount = schema.inclusionCriteria.length;
  const exclusionCount = schema.exclusionCriteria.length;
  const variableCount = schema.variables.length;
  const outcomeCount = schema.outcomes.length;

  const narrative = `The emulated protocol targets ${schema.population.toLowerCase()} and pursues the objective "${schema.objective}". ` +
    `Eligibility logic currently lists ${inclusionCount} inclusion criterion${inclusionCount === 1 ? '' : 'a'} and ${exclusionCount} exclusion criterion${exclusionCount === 1 ? '' : 'a'}. ` +
    `Downstream agents will derive ${variableCount} covariate${variableCount === 1 ? '' : 's'} and monitor ${outcomeCount} outcome${outcomeCount === 1 ? '' : 's'} for analysis.`;

  return {
    schema: deepClone(schema),
    narrative,
  };
}

function buildCohortSection(cohort: CohortResult | null): ReportCohortSection {
  if (!cohort) {
    return {
      summary: null,
      narrative:
        'Cohort generation has not been finalised. Trigger the cohort synthesis step to populate demographics and provenance.',
      keyMetrics: [],
    };
  }

  const summary = cohort.summary;
  const datasetLabel = formatDatasetLabel(summary.datasetId);
  const femaleRatio = summary.sex.proportions.F;
  const maleRatio = summary.sex.proportions.M;
  const keyMetrics = [
    { label: 'Dataset', value: datasetLabel },
    { label: 'Participants', value: `${summary.size}` },
    { label: 'Median age', value: `${summary.age.median} years` },
    { label: 'Female share', value: toPercent(femaleRatio) },
    { label: 'Male share', value: toPercent(maleRatio) },
  ];

  const narrative = `Using ${datasetLabel}, the emulation derived a cohort of n=${summary.size} participants. ` +
    `Median age is ${summary.age.median} years (range ${summary.age.min}-${summary.age.max}), with mean age ${summary.age.mean}. ` +
    `Sex distribution indicates ${toPercent(femaleRatio)} female and ${toPercent(maleRatio)} male representation.`;

  return {
    summary,
    narrative,
    keyMetrics,
  };
}

function buildHazardRatioSummary(run: AnalysisRunResult, cohort: CohortResult | null): ReportResultsSection {
  const table = run.tables.find((item) => item.id === 'hazard-table');
  const treatmentRow = table?.rows.find((row) => row.label.toLowerCase() === 'treatment');
  const hazardRatio = coerceNumber(treatmentRow?.values.hazardRatio);
  const lower = coerceNumber(treatmentRow?.values.lowerCI);
  const upper = coerceNumber(treatmentRow?.values.upperCI);
  const pValue = coerceNumber(treatmentRow?.values.pValue);
  const cohortSize = cohort?.summary.size ?? null;

  const keyFindings: string[] = [];
  if (hazardRatio !== null && lower !== null && upper !== null) {
    keyFindings.push(formatKeyFinding('HR', `${hazardRatio.toFixed(2)} (95% CI ${lower.toFixed(2)}-${upper.toFixed(2)})`));
  }
  if (pValue !== null) {
    keyFindings.push(formatKeyFinding('p-value', pValue < 0.001 ? '<0.001' : pValue.toFixed(3)));
  }

  const narrative = `The latest Cox Hazard Ratio analysis${cohortSize ? ` (n=${cohortSize})` : ''} produced an HR of ${
    hazardRatio !== null ? hazardRatio.toFixed(2) : 'pending'
  } with a 95% confidence interval spanning ${
    lower !== null && upper !== null ? `${lower.toFixed(2)}-${upper.toFixed(2)}` : 'pending bounds'
  } and ${
    pValue !== null ? `p=${pValue < 0.001 ? '<0.001' : pValue.toFixed(3)}` : 'no p-value yet'
  }.`;

  return {
    analysis: run,
    narrative,
    keyFindings,
  };
}

function buildPropensitySummary(run: AnalysisRunResult, cohort: CohortResult | null): ReportResultsSection {
  const balanceTable = run.tables.find((item) => item.id === 'balance-table');
  const divergences = balanceTable?.rows.map((row) => coerceNumber(row.values.stdDiff)).filter((value): value is number => value !== null) ?? [];
  const meanStdDiff =
    divergences.length > 0
      ? divergences.reduce((acc, value) => acc + Math.abs(value), 0) / divergences.length
      : null;
  const worstStdDiff = divergences.length > 0 ? Math.max(...divergences.map((value) => Math.abs(value))) : null;
  const cohortSize = cohort?.summary.size ?? null;

  const keyFindings: string[] = [];
  if (meanStdDiff !== null) {
    keyFindings.push(formatKeyFinding('Mean |std diff|', meanStdDiff.toFixed(2)));
  }
  if (worstStdDiff !== null) {
    keyFindings.push(formatKeyFinding('Max |std diff|', worstStdDiff.toFixed(2)));
  }

  const narrative = `Propensity score weighting${cohortSize ? ` (n=${cohortSize})` : ''} achieved covariate balance with an average absolute standardised difference of ${
    meanStdDiff !== null ? meanStdDiff.toFixed(2) : 'pending'
  }. The worst-case imbalance measured ${worstStdDiff !== null ? worstStdDiff.toFixed(2) : 'pending'}.`;

  return {
    analysis: run,
    narrative,
    keyFindings,
  };
}

function buildOutcomeDiffSummary(run: AnalysisRunResult, cohort: CohortResult | null): ReportResultsSection {
  const outcomeTable = run.tables.find((item) => item.id === 'outcome-table');
  const treated = outcomeTable?.rows.find((row) => row.label.toLowerCase() === 'treatment');
  const control = outcomeTable?.rows.find((row) => row.label.toLowerCase() === 'control');
  const treatedMean = coerceNumber(treated?.values.mean);
  const controlMean = coerceNumber(control?.values.mean);
  const treatedN = coerceNumber(treated?.values.n);
  const controlN = coerceNumber(control?.values.n);
  const effect =
    treatedMean !== null && controlMean !== null ? Number((treatedMean - controlMean).toFixed(3)) : null;
  const cohortSize = cohort?.summary.size ?? null;

  const keyFindings: string[] = [];
  if (effect !== null) {
    keyFindings.push(formatKeyFinding('Effect (treated - control)', effect.toFixed(3)));
  }
  if (treatedN !== null && controlN !== null) {
    keyFindings.push(formatKeyFinding('Sample split', `${treatedN} treated / ${controlN} control`));
  }

  const narrative = `Difference-in-means estimation${cohortSize ? ` (n=${cohortSize})` : ''} yielded an effect of ${
    effect !== null ? effect.toFixed(3) : 'pending'
  } when comparing treated and control cohorts.`;

  return {
    analysis: run,
    narrative,
    keyFindings,
  };
}

function buildResultsSection(run: AnalysisRunResult | null, cohort: CohortResult | null): ReportResultsSection {
  if (!run) {
    return {
      analysis: null,
      narrative:
        'Statistical analysis has not been executed. Run at least one template in the analysis workspace to populate quantitative findings.',
      keyFindings: [],
    };
  }

  if (run.templateId === 'hazard-ratio') {
    return buildHazardRatioSummary(run, cohort);
  }
  if (run.templateId === 'propensity-score') {
    return buildPropensitySummary(run, cohort);
  }
  return buildOutcomeDiffSummary(run, cohort);
}

function resolveArticles(ids: string[]): Article[] {
  if (ids.length === 0) return [];
  const lookup = new Set(ids);
  return ARTICLES.filter((article) => lookup.has(article.id));
}

function buildReferences(articles: Article[]): string[] {
  if (articles.length === 0) {
    return [
      'TrialSynth Team. Placeholder reference — update once literature selection is finalised.',
    ];
  }
  return articles.map((article) => {
    const leadAuthor = article.authors[0] ?? 'Unknown';
    return `${leadAuthor} et al. (${article.year}). ${article.title}. ${article.journal}.`;
  });
}

function buildAbstract(
  schema: TrialSchema | null,
  cohortSection: ReportCohortSection,
  resultsSection: ReportResultsSection,
  articles: Article[],
): string {
  const title = schema?.title ?? 'Unnamed trial emulation';
  const cohortSummary = cohortSection.summary;
  const datasetLabel = formatDatasetLabel(cohortSummary?.datasetId);
  const participants = cohortSummary?.size;
  const primaryFinding = resultsSection.keyFindings[0];
  const literatureCount = articles.length;

  const sentences: string[] = [
    `This draft real-world evidence report summarises the emulation "${title}" leveraging multi-agent extraction and synthesis across the TrialSynth pipeline.`,
  ];

  if (cohortSummary) {
    sentences.push(
      `A cohort of n=${participants} patients was derived from ${datasetLabel}, with median age ${cohortSummary.age.median} years and ${toPercent(
        cohortSummary.sex.proportions.F,
      )} female representation.`,
    );
  } else {
    sentences.push('Cohort derivation is still pending; the demographic summary will populate once synthesised.');
  }

  if (primaryFinding) {
    sentences.push(`Preliminary analytics highlight ${primaryFinding.toLowerCase()} in the latest statistical template run.`);
  } else {
    sentences.push('Statistical analyses are awaiting execution to surface quantitative findings.');
  }

  sentences.push(
    literatureCount > 0
      ? `Source material references ${literatureCount} curated publication${literatureCount === 1 ? '' : 's'}; see Appendix for citations.`
      : 'Literature references will populate automatically after selecting articles in the search workspace.',
  );

  return sentences.join(' ');
}

export function loadLatestSchemaDraft(selectedArticleIds: string[]): TrialSchema | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const storageKey = getSchemaStorageKey(selectedArticleIds);
  const raw = window.localStorage.getItem(storageKey);
  const versions = loadStoredVersions(raw);
  const latest = versions.at(-1);
  return latest ? deepClone(latest.schema) : null;
}

interface BuildReportParams {
  selectedArticleIds: string[];
  cohort: CohortResult | null;
  analysisRuns: AnalysisRunResult[];
  schema?: TrialSchema | null;
}

export function buildReportData({
  selectedArticleIds,
  cohort,
  analysisRuns,
  schema,
}: BuildReportParams): ReportData {
  const resolvedSchema = schema ?? loadLatestSchemaDraft(selectedArticleIds);
  const articles = resolveArticles(selectedArticleIds);
  const primaryAnalysis = extractPrimaryAnalysis(analysisRuns);
  const methods = buildMethodsSection(resolvedSchema);
  const cohortSection = buildCohortSection(cohort);
  const results = buildResultsSection(primaryAnalysis, cohort);
  const references = buildReferences(articles);

  const abstract = buildAbstract(resolvedSchema, cohortSection, results, articles);

  const authorCandidates = new Set<string>();
  if (resolvedSchema?.version.author) {
    authorCandidates.add(resolvedSchema.version.author);
  }
  if (articles[0]?.authors[0]) {
    authorCandidates.add(`${articles[0].authors[0]} (curated)`);
  }
  authorCandidates.add('TrialSynth Report Agent');

  const discussion =
    'These findings constitute an automatically generated draft. Clinical review should validate adherence to the study objective, confirm dataset appropriateness, and extend interpretation before dissemination.';

  return {
    title: resolvedSchema?.title ?? 'TrialSynth Report Draft',
    authors: Array.from(authorCandidates),
    abstract,
    methods,
    cohort: cohortSection,
    results,
    discussion,
    references,
    createdAt: new Date().toISOString(),
  };
}
