export type TrialVariableType =
  | 'categorical'
  | 'numeric'
  | 'boolean'
  | 'text'
  | 'date';

export interface TrialVariable {
  id: string;
  name: string;
  type: TrialVariableType;
  description: string;
  required: boolean;
  sourceHint?: string;
}

export interface TrialOutcome {
  id: string;
  name: string;
  description: string;
  metric: string;
}

export interface SchemaMetadata {
  journal: string;
  year: number | null;
  source: string;
  populationSynopsis?: string;
}

export interface SchemaVersionMeta {
  rev: number;
  author: string;
  timestamp: string; // ISO string for deterministic storage
  message: string;
}

export interface TrialSchema {
  id: string;
  title: string;
  objective: string;
  population: string;
  inclusionCriteria: string[];
  exclusionCriteria: string[];
  variables: TrialVariable[];
  outcomes: TrialOutcome[];
  metadata: SchemaMetadata;
  version: SchemaVersionMeta;
  notes?: string;
}

export interface SchemaValidationIssue {
  id: string;
  message: string;
  path: string;
  severity: 'error' | 'warning';
}

export interface SchemaVersionSnapshot {
  schema: TrialSchema;
  changes: string[];
}

export type SchemaSection =
  | 'overview'
  | 'criteria'
  | 'variables'
  | 'outcomes'
  | 'metadata';
