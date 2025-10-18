import type { Article } from '../types';
import rawArticles from '../../../../public/data/fixtures/articles.json';

export const ARTICLES: Article[] = rawArticles as Article[];

export const ARTICLE_YEARS = Array.from(
  new Set(ARTICLES.map((article) => article.year)),
)
  .sort((a, b) => b - a)
  .map((year) => ({ label: `${year}`, value: year }));

export const SOURCE_OPTIONS: Array<{ label: string; value: Article['source'] }> = [
  { label: 'PubMed', value: 'PubMed' },
  { label: 'ClinicalTrials.gov', value: 'CTgov' },
];
