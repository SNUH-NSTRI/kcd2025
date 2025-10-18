import type { DatasetOption } from './types';

export const DATASET_OPTIONS: DatasetOption[] = [
  {
    id: 'mimic-iv',
    label: 'MIMIC-IV v3.1',
    description: 'Real de-identified ICU patient data from MIMIC-IV database.',
  },
  {
    id: 'k-mimic',
    label: 'K-MIMIC Stub',
    description: 'Korean federation dataset placeholder.',
  },
  {
    id: 'demo',
    label: 'Local Demo',
    description: 'Lightweight sample for testing (deprecated).',
  },
];

export const MIN_COHORT_SIZE = 30;
export const MAX_COHORT_SIZE = 500;
