import type { PatientRecord } from '../types';
import type { CohortSummary, CohortPatient } from '@/features/flow/types';

/**
 * Parse CSV text into patient records
 */
export function parseCohortCSV(csvText: string): PatientRecord[] {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) {
    return [];
  }

  const headers = lines[0]!.split(',');
  const patients: PatientRecord[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i]!.split(',');
    const row: Record<string, string> = {};

    headers.forEach((header, index) => {
      row[header] = values[index] ?? '';
    });

    // Extract core patient info
    const subject_id = row['subject_id'] ?? '';
    const age = parseInt(row['age_at_admission'] ?? '0', 10);
    // MIMIC-IV doesn't expose sex directly for privacy, default to 'M'
    const sexValue = row['sex'] ?? 'M';
    const sex = (sexValue === 'F' ? 'F' : 'M') as 'M' | 'F';

    // All other columns go into vars
    const vars: Record<string, unknown> = {};
    Object.entries(row).forEach(([key, value]) => {
      if (key !== 'subject_id' && key !== 'age_at_admission') {
        // Try to parse as number
        const numValue = parseFloat(value);
        vars[key] = isNaN(numValue) ? value : numValue;
      }
    });

    patients.push({
      id: subject_id,
      age,
      sex,
      vars,
    });
  }

  return patients;
}

/**
 * Generate cohort summary from real patient data
 */
export function summarizeCohort(patients: PatientRecord[]): CohortSummary {
  const size = patients.length;

  // Calculate age statistics
  const ages = patients.map(p => p.age).sort((a, b) => a - b);
  const mean = ages.reduce((sum, age) => sum + age, 0) / size;
  const median = size % 2 === 0
    ? (ages[size / 2 - 1]! + ages[size / 2]!) / 2
    : ages[Math.floor(size / 2)]!;
  const min = Math.min(...ages);
  const max = Math.max(...ages);

  // Create age histogram buckets
  const bucketSize = 10;
  const numBuckets = Math.ceil((max - min) / bucketSize);
  const histogram = Array.from({ length: numBuckets }, (_, i) => {
    const rangeStart = min + i * bucketSize;
    const rangeEnd = rangeStart + bucketSize;
    const count = ages.filter(age => age >= rangeStart && age < rangeEnd).length;
    return {
      label: `${rangeStart}-${rangeEnd}`,
      range: [rangeStart, rangeEnd] as [number, number],
      count,
    };
  });

  // Count sex distribution (MIMIC-IV doesn't expose sex for privacy, use 'U' for unknown)
  const sexCounts: Record<'M' | 'F', number> = { M: 0, F: 0 };
  patients.forEach(patient => {
    if (patient.sex === 'M') sexCounts.M++;
    else if (patient.sex === 'F') sexCounts.F++;
  });

  const sexProportions: Record<'M' | 'F', number> = {
    M: sexCounts.M / size,
    F: sexCounts.F / size,
  };

  return {
    size,
    age: {
      mean: Math.round(mean * 10) / 10,
      median: Math.round(median * 10) / 10,
      min,
      max,
      histogram,
    },
    sex: {
      counts: sexCounts,
      proportions: sexProportions,
    },
    datasetId: 'mimic-iv',
  };
}
