import type {
  AnalysisChart,
  AnalysisRunResult,
  AnalysisTable,
  AnalysisTemplateMeta,
  CohortResult,
} from '@/features/flow/types';
import { createSeededRng } from '@/features/cohort/lib/random';

const BALANCE_VARIABLES = ['Age', 'BMI', 'HbA1c', 'Creatinine', 'Statin use'];
const SURVIVAL_TIMES = [0, 30, 60, 120, 180, 240, 360];
const OUTCOME_GROUPS = ['Control', 'Treatment'];

function buildBalanceTable(rng: ReturnType<typeof createSeededRng>): AnalysisTable {
  const rows = BALANCE_VARIABLES.map((variable) => {
    const treated = Number((rng.nextFloat(0.2, 0.8)).toFixed(2));
    const control = Number((treated + rng.nextFloat(-0.1, 0.1)).toFixed(2));
    const stdDiff = Number((treated - control).toFixed(2));
    return {
      label: variable,
      values: {
        treated,
        control,
        stdDiff,
      },
    };
  });

  return {
    id: 'balance-table',
    title: 'Covariate Balance (Standardised Differences)',
    columns: ['treated', 'control', 'stdDiff'],
    rows,
  };
}

function buildPsChart(rng: ReturnType<typeof createSeededRng>): AnalysisChart {
  const points = Array.from({ length: 20 }, (_, index) => {
    const x = Number((index / 20).toFixed(2));
    const treated = Number((rng.nextFloat(0, 1)).toFixed(2));
    const control = Number((rng.nextFloat(0, 1)).toFixed(2));
    return { x, treated, control };
  });

  return {
    id: 'ps-distribution',
    type: 'line',
    title: 'Propensity Score Distribution',
    series: [
      {
        id: 'treated',
        label: 'Treated',
        points: points.map((point) => ({ x: point.x, y: point.treated })),
      },
      {
        id: 'control',
        label: 'Control',
        points: points.map((point) => ({ x: point.x, y: point.control })),
      },
    ],
    xLabel: 'Propensity score',
    yLabel: 'Density',
  };
}

function buildHazardTable(rng: ReturnType<typeof createSeededRng>): AnalysisTable {
  return {
    id: 'hazard-table',
    title: 'Cox Model Hazard Ratios',
    columns: ['hazardRatio', 'lowerCI', 'upperCI', 'pValue'],
    rows: OUTCOME_GROUPS.map((group, index) => {
      const hr = index === 0 ? 1 : rng.nextFloat(0.7, 1.4);
      const lower = Number((hr - rng.nextFloat(0.05, 0.15)).toFixed(2));
      const upper = Number((hr + rng.nextFloat(0.05, 0.15)).toFixed(2));
      return {
        label: group,
        values: {
          hazardRatio: Number(hr.toFixed(2)),
          lowerCI: lower,
          upperCI: upper,
          pValue: Number(rng.nextFloat(0.01, 0.2).toFixed(3)),
        },
      };
    }),
  };
}

function buildSurvivalChart(rng: ReturnType<typeof createSeededRng>): AnalysisChart {
  return {
    id: 'survival-curve',
    type: 'line',
    title: 'Kaplan–Meier Survival Curve',
    series: OUTCOME_GROUPS.map((group) => ({
      id: group,
      label: group,
      points: SURVIVAL_TIMES.map((time) => {
        const base = group === 'Treatment' ? 0.85 : 0.8;
        const decay = rng.nextFloat(0.005, 0.02) * time;
        const y = Number(Math.max(0.1, base - decay / 10).toFixed(2));
        return {
          x: time,
          y,
          lower: Number((y - rng.nextFloat(0.02, 0.05)).toFixed(2)),
          upper: Number((y + rng.nextFloat(0.02, 0.05)).toFixed(2)),
        };
      }),
    })),
    xLabel: 'Days since index',
    yLabel: 'Survival probability',
  };
}

function buildOutcomeTable(rng: ReturnType<typeof createSeededRng>): AnalysisTable {
  return {
    id: 'outcome-table',
    title: 'Outcome Difference-in-Means',
    columns: ['mean', 'stdDev', 'n'],
    rows: OUTCOME_GROUPS.map((group) => ({
      label: group,
      values: {
        mean: Number(rng.nextFloat(0.3, 0.8).toFixed(2)),
        stdDev: Number(rng.nextFloat(0.1, 0.3).toFixed(2)),
        n: rng.nextInt(60, 120),
      },
    })),
  };
}

function buildEffectChart(rng: ReturnType<typeof createSeededRng>): AnalysisChart {
  const effect = rng.nextFloat(-0.15, 0.15);
  return {
    id: 'effect-size',
    type: 'bar',
    title: 'Effect Size with Confidence Interval',
    series: [
      {
        id: 'difference',
        label: 'Treatment effect',
        points: [
          {
            x: 0,
            y: Number(effect.toFixed(3)),
            lower: Number((effect - 0.05).toFixed(3)),
            upper: Number((effect + 0.05).toFixed(3)),
          },
        ],
      },
    ],
    xLabel: 'Effect',
    yLabel: 'Difference in means',
  };
}

export function synthesiseAnalysisResult(
  template: AnalysisTemplateMeta,
  cohort: CohortResult,
  runId: string,
  startedAt: string,
): AnalysisRunResult {
  const rng = createSeededRng(`${runId}|${template.id}|${cohort.seed}`);
  const baseDuration = rng.nextInt(1400, 2600);
  const finishedAt = new Date(Date.parse(startedAt) + baseDuration).toISOString();

  if (template.id === 'propensity-score') {
    return {
      runId,
      templateId: template.id,
      startedAt,
      finishedAt,
      durationMs: baseDuration,
      tables: [buildBalanceTable(rng)],
      charts: [buildPsChart(rng)],
      notes: 'Weights converge after three iterations; overlap diagnostics within acceptable thresholds.',
    };
  }

  if (template.id === 'hazard-ratio') {
    return {
      runId,
      templateId: template.id,
      startedAt,
      finishedAt,
      durationMs: baseDuration,
      tables: [buildHazardTable(rng)],
      charts: [buildSurvivalChart(rng)],
      notes: 'Cox model adjusted for age, sex, and renal function. Schoenfeld residuals stable.',
    };
  }

  return {
    runId,
    templateId: template.id,
    startedAt,
    finishedAt,
    durationMs: baseDuration,
    tables: [buildOutcomeTable(rng)],
    charts: [buildEffectChart(rng)],
    notes: 'Bootstrap-adjusted difference-in-means with 1,000 resamples.',
  };
}
