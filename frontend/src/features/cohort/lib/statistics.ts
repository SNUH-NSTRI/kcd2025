import type { CohortAgeSummary, CohortResult, CohortSexSummary } from '@/features/flow/types';
import type { PatientRecord } from '../types';

export function computeMean(values: number[]): number {
  if (values.length === 0) return 0;
  const total = values.reduce((acc, value) => acc + value, 0);
  return total / values.length;
}

export function computeMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

function buildAgeHistogram(values: number[]): CohortAgeSummary['histogram'] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const bucketSize = 10;
  const bucketCount = Math.max(4, Math.ceil((max - min) / bucketSize));
  const histogram = Array.from({ length: bucketCount }, (_, index) => {
    const start = Math.floor(min / bucketSize) * bucketSize + index * bucketSize;
    const end = start + bucketSize - 1;
    return {
      label: `${start}-${end}`,
      range: [start, end] as [number, number],
      count: 0,
    };
  });

  values.forEach((value) => {
    const index = Math.min(
      histogram.length - 1,
      Math.max(0, Math.floor((value - histogram[0].range[0]) / bucketSize)),
    );
    histogram[index].count += 1;
  });

  return histogram;
}

export function summarisePatients(patients: PatientRecord[], datasetId: CohortResult['summary']['datasetId']) {
  const ages = patients.map((patient) => patient.age);
  const ageSummary: CohortAgeSummary = {
    mean: Number(computeMean(ages).toFixed(1)),
    median: Number(computeMedian(ages).toFixed(1)),
    min: ages.length ? Math.min(...ages) : 0,
    max: ages.length ? Math.max(...ages) : 0,
    histogram: buildAgeHistogram(ages),
  };

  const male = patients.filter((patient) => patient.sex === 'M').length;
  const female = patients.filter((patient) => patient.sex === 'F').length;
  const total = Math.max(1, patients.length);
  const sexSummary: CohortSexSummary = {
    counts: {
      M: male,
      F: female,
    },
    proportions: {
      M: Number((male / total).toFixed(2)),
      F: Number((female / total).toFixed(2)),
    },
  };

  return {
    size: patients.length,
    age: ageSummary,
    sex: sexSummary,
    datasetId,
  } as CohortResult['summary'];
}
