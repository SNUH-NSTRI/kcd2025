import type { CohortDatasetId, CohortPatient, CohortResult } from '@/features/flow/types';

export type DictionaryFieldType = 'numeric' | 'categorical' | 'boolean' | 'text' | 'date';

export interface DictionaryField {
  id: string;
  label: string;
  type: DictionaryFieldType;
  description: string;
  tags?: string[];
  categories?: string[];
  range?: { min: number; max: number };
  decimals?: number;
}

export interface DatasetOption {
  id: CohortDatasetId;
  label: string;
  description: string;
}

export interface GeneratedCohort extends CohortResult {}

export interface MappingSuggestion {
  variableId: string;
  candidateFieldId: string;
  confidence: number;
}

export type PatientRecord = CohortPatient;
