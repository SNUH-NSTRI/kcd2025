import type { Article } from './types';

export const PAGE_SIZE_OPTIONS = [5, 10, 15];

export const SOURCE_LABELS: Record<Article['source'], string> = {
  PubMed: 'PubMed',
  CTgov: 'ClinicalTrials.gov',
};

export const DEFAULT_SEARCH_PLACEHOLDER =
  'Enter keywords (e.g., cardiovascular, metformin)';
