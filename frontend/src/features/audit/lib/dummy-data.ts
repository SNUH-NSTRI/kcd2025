import { DEFAULT_ACTOR } from '../constants';
import type { AuditEvent } from '../types';

function daysAgo(days: number, hoursOffset = 0): number {
  return Date.now() - days * 24 * 60 * 60 * 1000 - hoursOffset * 60 * 60 * 1000;
}

export function getSeedAuditEvents(): AuditEvent[] {
  const seeds: AuditEvent[] = [
    {
      id: 'seed-schema-001',
      ts: daysAgo(2, -3),
      actor: DEFAULT_ACTOR,
      entity: 'schema',
      action: 'schema.version.commit',
      metadata: {
        summary: 'Saved schema revision 5 after reviewer feedback.',
        rev: 5,
        articles: ['cardio-outcomes', 'oncology-insights'],
      },
    },
    {
      id: 'seed-cohort-001',
      ts: daysAgo(1, 2),
      actor: DEFAULT_ACTOR,
      entity: 'cohort',
      action: 'cohort.generated',
      metadata: {
        summary: 'Synthesised cohort with mapped ICU encounter variables.',
        datasetId: 'mimic-iv',
        size: 1234,
        mappedVariables: 18,
      },
    },
    {
      id: 'seed-analysis-001',
      ts: daysAgo(1, 1),
      actor: 'Automation Service',
      entity: 'analysis',
      action: 'analysis.run.completed',
      metadata: {
        summary: 'Completed propensity score matching run.',
        templateId: 'psm-matching',
        durationMs: 5400,
        runId: 'seed-run-001',
      },
    },
    {
      id: 'seed-report-001',
      ts: daysAgo(0, 5),
      actor: 'Automation Service',
      entity: 'report',
      action: 'report.generated',
      metadata: {
        summary: 'Generated RWE report for ICU sepsis cohort.',
        sections: ['executive-summary', 'outcomes', 'methodology'],
        articleCount: 2,
      },
    },
    {
      id: 'seed-flow-001',
      ts: daysAgo(5, 4),
      actor: DEFAULT_ACTOR,
      entity: 'flow',
      action: 'flow.step.completed',
      metadata: {
        summary: 'Marked analysis step complete to unlock reporting.',
        step: 'analysis',
      },
    },
    {
      id: 'seed-schema-002',
      ts: daysAgo(7, 3),
      actor: DEFAULT_ACTOR,
      entity: 'schema',
      action: 'schema.version.revert',
      metadata: {
        summary: 'Reverted schema to revision 3 due to validation findings.',
        fromRev: 4,
        toRev: 3,
      },
    },
    {
      id: 'seed-cohort-002',
      ts: daysAgo(8, -2),
      actor: 'Automation Service',
      entity: 'cohort',
      action: 'cohort.mapping.suggestion',
      metadata: {
        summary: 'Accepted auto-mapping suggestions for ventilator settings.',
        variables: ['ventilation_mode', 'fio2_ratio'],
      },
    },
    {
      id: 'seed-analysis-002',
      ts: daysAgo(10, 1),
      actor: 'Compliance Monitor',
      entity: 'analysis',
      action: 'analysis.run.failed',
      metadata: {
        summary: 'Kaplan-Meier analysis failed due to missing censoring dates.',
        templateId: 'km-survival',
        error: 'Missing required variables: discharge_date',
      },
    },
    {
      id: 'seed-report-002',
      ts: daysAgo(14, 6),
      actor: 'Compliance Monitor',
      entity: 'report',
      action: 'report.shared',
      metadata: {
        summary: 'Exported PDF report for weekly clinical sync.',
        format: 'pdf',
        recipients: ['compliance@trial-synth.ai'],
      },
    },
    {
      id: 'seed-flow-002',
      ts: daysAgo(20, -1),
      actor: DEFAULT_ACTOR,
      entity: 'flow',
      action: 'flow.session.resumed',
      metadata: {
        summary: 'Resumed workflow from saved checkpoint.',
        currentStep: 'schema',
      },
    },
  ];

  return seeds.sort((a, b) => b.ts - a.ts);
}
