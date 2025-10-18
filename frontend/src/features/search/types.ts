export interface Article {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  journal: string;
  year: number;
  source: 'PubMed' | 'CTgov';
  keywords: string[];
  meshTerms: string[];
}
