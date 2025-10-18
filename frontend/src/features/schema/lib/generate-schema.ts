import type { Article } from '@/features/search/types';
import {
  DEFAULT_VERSION_AUTHOR,
  INITIAL_VERSION_MESSAGE,
} from '../constants';
import type { TrialOutcome, TrialSchema, TrialVariable, TrialVariableType } from '../types';
import { generateId, toIsoString } from './utils';

const KEYWORD_TYPE_RULES: Array<{
  matches: string[];
  type: TrialVariableType;
}> = [
  { matches: ['age', 'score', 'rate', 'ratio', 'pressure', 'index', 'trajectory'], type: 'numeric' },
  { matches: ['dose', 'intensity', 'level', 'duration', 'time'], type: 'numeric' },
  { matches: ['sex', 'gender', 'class', 'group', 'stage'], type: 'categorical' },
  { matches: ['therapy', 'treatment', 'exposure', 'use', 'status'], type: 'boolean' },
  { matches: ['biomarker', 'severity', 'scale'], type: 'numeric' },
];

function inferVariableType(keyword: string): TrialVariableType {
  const normalized = keyword.toLowerCase();
  for (const rule of KEYWORD_TYPE_RULES) {
    if (rule.matches.some((fragment) => normalized.includes(fragment))) {
      return rule.type;
    }
  }
  return 'text';
}

function buildVariables(articles: Article[]): TrialVariable[] {
  const taken = new Set<string>();
  const variables: TrialVariable[] = [];

  articles.forEach((article) => {
    article.keywords.forEach((keyword, index) => {
      const key = keyword.toLowerCase();
      if (taken.has(key)) return;
      taken.add(key);
      const type = inferVariableType(keyword);
      variables.push({
        id: generateId('var'),
        name: keyword.replace(/(^.|\s.)/g, (char) => char.toUpperCase()),
        type,
        description: `Feature engineered from keyword "${keyword}" in ${article.title}.`,
        required: index === 0,
        sourceHint: article.id,
      });
    });
  });

  if (variables.length === 0) {
    variables.push({
      id: generateId('var'),
      name: 'Primary Exposure',
      type: 'text',
      description: 'Add at least one keyword-derived variable to proceed.',
      required: true,
    });
  }

  return variables;
}

function buildCriteria(articles: Article[]) {
  const inclusion = new Set<string>();
  const exclusion = new Set<string>();

  articles.forEach((article) => {
    const leadingKeyword = article.keywords[0];
    if (leadingKeyword) {
      inclusion.add(`Evidence of ${leadingKeyword.toLowerCase()} documented in source data.`);
    }
    inclusion.add(`Age range aligned with ${article.journal} publication (${article.year}).`);
    exclusion.add(`Conflicting registry records compared with ${article.title}.`);
  });

  return {
    inclusionCriteria: Array.from(inclusion),
    exclusionCriteria: Array.from(exclusion),
  };
}

function buildOutcomes(articles: Article[]): TrialOutcome[] {
  const outcomes: TrialOutcome[] = [];
  const used = new Set<string>();

  articles.forEach((article) => {
    article.meshTerms.forEach((term) => {
      const key = term.toLowerCase();
      if (used.has(key)) return;
      used.add(key);
      outcomes.push({
        id: generateId('outcome'),
        name: term,
        description: `Monitor ${term.toLowerCase()} signals across cohorts based on ${article.title}.`,
        metric: term.toLowerCase().includes('mortality') ? 'hazard ratio' : 'relative risk',
      });
    });
  });

  if (outcomes.length === 0) {
    outcomes.push({
      id: generateId('outcome'),
      name: 'Composite clinical outcome',
      description: 'Define the primary endpoint derived from aggregated evidence.',
      metric: 'risk difference',
    });
  }

  return outcomes;
}

function summarizePopulation(articles: Article[]): string {
  const primary = articles[0];
  if (!primary) {
    return 'Define the target cohort and relevant baseline characteristics.';
  }

  const keywordPart = primary.keywords.slice(0, 2).join(', ');
  const base = keywordPart
    ? `Individuals related to ${keywordPart.toLowerCase()}`
    : 'Individuals aligned with study inclusion criteria';

  return `${base} described in ${primary.journal} (${primary.year}).`;
}

function deriveObjective(articles: Article[]): string {
  const primary = articles[0];
  if (!primary) {
    return 'Outline the clinical question and measures of effectiveness to emulate the trial.';
  }
  const sentences = primary.abstract.split(/(?<=[.!?])\s+/);
  return sentences[0] ?? primary.abstract;
}

export function generateInitialSchema(articles: Article[]): TrialSchema {
  const now = new Date();
  const { inclusionCriteria, exclusionCriteria } = buildCriteria(articles);
  const schema: TrialSchema = {
    id: generateId('schema'),
    title: articles[0]?.title ?? 'Untitled trial schema',
    objective: deriveObjective(articles),
    population: summarizePopulation(articles),
    inclusionCriteria,
    exclusionCriteria,
    variables: buildVariables(articles).slice(0, 12),
    outcomes: buildOutcomes(articles).slice(0, 10),
    metadata: {
      journal: articles[0]?.journal ?? '',
      year: articles[0]?.year ?? null,
      source: articles[0]?.source ?? 'PubMed',
      populationSynopsis: articles
        .map((article) => `${article.title} (${article.year})`)
        .join(' | '),
    },
    notes: 'Auto-generated draft derived from curated literature. Refine fields prior to cohort execution.',
    version: {
      rev: 1,
      author: DEFAULT_VERSION_AUTHOR,
      timestamp: toIsoString(now),
      message: INITIAL_VERSION_MESSAGE,
    },
  };

  return schema;
}
