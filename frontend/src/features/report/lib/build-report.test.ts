import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { AnalysisRunResult, CohortResult } from '../../flow/types';
import type { TrialSchema } from '../../schema/types';
import { buildReportData } from './build-report';

const mockSchema: TrialSchema = {
  id: 'schema-001',
  title: 'ACE Inhibitors for CKD Patients',
  objective: 'Evaluate renal outcomes under ACE inhibitor therapy.',
  population: 'Adults with chronic kidney disease stages 3-4.',
  inclusionCriteria: ['Age ≥ 18', 'eGFR between 30-59'],
  exclusionCriteria: ['Renal transplant', 'Pregnancy'],
  variables: [
    {
      id: 'age',
      name: 'Age',
      type: 'numeric',
      description: 'Age at index date',
      required: true,
    },
  ],
  outcomes: [
    {
      id: 'renal-decline',
      name: 'Renal decline',
      description: '30% decline in eGFR',
      metric: 'hazardRatio',
    },
  ],
  metadata: {
    journal: 'Kidney International',
    year: 2022,
    source: 'PubMed',
  },
  version: {
    rev: 1,
    author: 'TrialSynth Agent',
    timestamp: new Date().toISOString(),
    message: 'Auto-generated',
  },
};

const mockCohort: CohortResult = {
  patients: [],
  summary: {
    size: 212,
    datasetId: 'mimic-iv',
    age: {
      mean: 67,
      median: 66,
      min: 42,
      max: 89,
      histogram: [],
    },
    sex: {
      counts: { F: 104, M: 108 },
      proportions: { F: 0.49, M: 0.51 },
    },
  },
  createdAt: new Date().toISOString(),
  seed: 'unit-test',
};

const hazardRun: AnalysisRunResult = {
  runId: 'run-123',
  templateId: 'hazard-ratio',
  startedAt: new Date(Date.now() - 2000).toISOString(),
  finishedAt: new Date().toISOString(),
  durationMs: 1800,
  tables: [
    {
      id: 'hazard-table',
      title: 'Cox Model Hazard Ratios',
      columns: ['hazardRatio', 'lowerCI', 'upperCI', 'pValue'],
      rows: [
        {
          label: 'Control',
          values: {
            hazardRatio: 1,
            lowerCI: 1,
            upperCI: 1,
            pValue: 1,
          },
        },
        {
          label: 'Treatment',
          values: {
            hazardRatio: 0.82,
            lowerCI: 0.73,
            upperCI: 0.94,
            pValue: 0.012,
          },
        },
      ],
    },
  ],
  charts: [],
  notes: 'Model converged in 16 iterations with acceptable residual diagnostics.',
};

describe('buildReportData', () => {
  it('binds cohort metrics and hazard ratio outputs into the draft narrative', () => {
    const report = buildReportData({
      selectedArticleIds: [],
      cohort: mockCohort,
      analysisRuns: [hazardRun],
      schema: mockSchema,
    });

    assert.ok(report.abstract.includes('n=212'));
    assert.ok(report.methods.schema);
    assert.strictEqual(report.results.analysis?.templateId, 'hazard-ratio');
    assert.ok(report.results.keyFindings.some((finding: string) => finding.startsWith('HR:')));
    assert.ok(/HR=0\.82/.test(report.results.narrative) || report.results.narrative.includes('0.82'));
    assert.ok(report.discussion.length > 0);
  });

  it('falls back to placeholder narratives when source data is missing', () => {
    const report = buildReportData({
      selectedArticleIds: [],
      cohort: null,
      analysisRuns: [],
      schema: null,
    });

    assert.strictEqual(report.methods.schema, null);
    assert.strictEqual(report.cohort.summary, null);
    assert.strictEqual(report.results.analysis, null);
    assert.ok(report.abstract.toLowerCase().includes('pending'));
    assert.ok(report.references[0].toLowerCase().includes('placeholder'));
  });
});
