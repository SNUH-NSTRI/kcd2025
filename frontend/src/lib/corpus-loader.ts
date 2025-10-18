/**
 * Load trial data from local corpus.json files
 */

export interface CorpusDocument {
  source: string;
  identifier: string;
  title: string;
  abstract: string;
  full_text?: string;
  fetched_at?: string;
  url?: string;
  metadata?: {
    nct_id: string;
    retrieved_at?: string;
    phase?: string[];
    conditions?: string[];
    status?: string;
    arms_interventions?: unknown;
    eligibility?: unknown;
    outcomes?: unknown;
  };
}

export interface CorpusData {
  schema_version: string;
  documents: CorpusDocument[];
}

/**
 * Load corpus.json for a given NCT ID from public/data/fixtures
 */
export async function loadCorpusData(nctId: string): Promise<CorpusData | null> {
  try {
    const response = await fetch(`/data/fixtures/datathon/${nctId}/corpus.json`);
    if (!response.ok) {
      console.warn(`Corpus not found for ${nctId}`);
      return null;
    }
    const data: CorpusData = await response.json();
    return data;
  } catch (error) {
    console.error(`Failed to load corpus for ${nctId}:`, error);
    return null;
  }
}

/**
 * Extract trial title from corpus data
 */
export function getTrialTitleFromCorpus(corpusData: CorpusData | null): string | null {
  if (!corpusData || !corpusData.documents || corpusData.documents.length === 0) {
    return null;
  }

  // Find the clinicaltrials document
  const ctDoc = corpusData.documents.find((doc) => doc.source === 'clinicaltrials');
  return ctDoc?.title || corpusData.documents[0]?.title || null;
}
