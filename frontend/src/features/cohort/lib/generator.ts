import type { CohortDatasetId, CohortResult } from '@/features/flow/types';
import type { TrialVariable } from '@/features/schema/types';
import { createSeededRng, type SeededRng } from './random';
import { summarisePatients } from './statistics';
import { COHORT_DICTIONARY, getDictionaryField } from './dictionary';
import type { DictionaryField, PatientRecord } from '../types';

interface GenerateCohortParams {
  variables: TrialVariable[];
  mapping: Record<string, string | null>;
  cohortSize: number;
  seed: string;
  datasetId: CohortDatasetId;
}

function resolvedSeed({
  seed,
  datasetId,
  mapping,
}: Pick<GenerateCohortParams, 'seed' | 'datasetId' | 'mapping'>): string {
  const entries = Object.entries(mapping)
    .filter(([, value]) => Boolean(value))
    .sort(([a], [b]) => a.localeCompare(b));
  const mappingSignature = entries.map(([key, value]) => `${key}:${value}`).join('|');
  return `${seed}|${datasetId}|${mappingSignature}`;
}

function sampleNumeric(field: DictionaryField, rng: SeededRng) {
  const { range, decimals } = field;
  const min = range?.min ?? 0;
  const max = range?.max ?? 100;
  const value = rng.nextFloat(min, max);
  if (typeof decimals === 'number') {
    return Number(value.toFixed(decimals));
  }
  return Math.round(value);
}

function sampleBoolean(rng: SeededRng) {
  return rng.boolean(0.5);
}

function sampleCategorical(field: DictionaryField, rng: SeededRng) {
  const categories = field.categories ?? ['A', 'B'];
  return rng.pick(categories);
}

function sampleDate(rng: SeededRng) {
  const now = Date.now();
  const offset = rng.nextFloat(-180, 30) * 24 * 60 * 60 * 1000;
  return new Date(now + offset).toISOString().slice(0, 10);
}

function generateValue(field: DictionaryField, rng: SeededRng) {
  switch (field.type) {
    case 'numeric':
      return sampleNumeric(field, rng);
    case 'boolean':
      return sampleBoolean(rng);
    case 'categorical':
      return sampleCategorical(field, rng);
    case 'date':
      return sampleDate(rng);
    case 'text':
    default:
      return `${field.label} note`;
  }
}

function buildPatient(index: number, rng: SeededRng, params: GenerateCohortParams): PatientRecord {
  const age = rng.nextInt(18, 90);
  const sex = rng.boolean(0.52) ? 'F' : 'M';
  const vars: Record<string, unknown> = {};

  params.variables.forEach((variable) => {
    const mappedFieldId = params.mapping[variable.id];
    if (!mappedFieldId) return;
    const field = getDictionaryField(mappedFieldId);
    if (!field) return;
    vars[variable.id] = generateValue(field, rng);
  });

  return {
    id: `${index + 1}`,
    age,
    sex,
    vars,
  };
}

export function generateCohort({
  variables,
  mapping,
  cohortSize,
  seed,
  datasetId,
}: GenerateCohortParams): CohortResult {
  const effectiveSeed = resolvedSeed({ seed, datasetId, mapping });
  const rng = createSeededRng(effectiveSeed);
  const size = Math.max(10, cohortSize);

  const patients: PatientRecord[] = Array.from({ length: size }, (_, index) =>
    buildPatient(index, rng, { variables, mapping, cohortSize: size, seed, datasetId }),
  );

  const summary = summarisePatients(patients, datasetId);

  return {
    patients,
    summary,
    createdAt: new Date().toISOString(),
    seed: effectiveSeed,
  };
}

export function suggestMappings(variables: TrialVariable[]): Record<string, string> {
  const suggestions: Record<string, string> = {};
  variables.forEach((variable) => {
    const normalized = variable.name.toLowerCase();
    const candidate = COHORT_DICTIONARY.find((field) =>
      field.label.toLowerCase().includes(normalized.split(' ')[0] ?? ''),
    );
    if (candidate) {
      suggestions[variable.id] = candidate.id;
    }
  });
  return suggestions;
}
